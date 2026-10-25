/**
 * llmService.js
 * -------------
 * Manages communication with the local LM Studio instance for the Stock-Specific AI Assistant.
 *
 * Architecture:
 *   React -> Node.js -> FastAPI -> FinSight stock analysis -> Local LLM / LM Studio -> Response -> React
 *
 * Responsibilities:
 *   - Auto-discover active model from GET /v1/models (never hardcode a random model name).
 *   - Build compact, structured stock context from real FinSight analysis (no raw candles).
 *   - Format authoritative system prompt enforcing guardrails.
 *   - Send conversation history + stock context to LM Studio chat completions.
 *   - Provide robust fallback/error reporting if LM Studio is offline or unavailable.
 */

import axios from 'axios';
import 'dotenv/config';

const LLM_BASE_URL = (process.env.LLM_BASE_URL || 'http://localhost:1234/v1').replace(/\/+$/, '');
const LLM_TIMEOUT = parseInt(process.env.LLM_TIMEOUT_MS || '45000', 10);
const CONFIGURED_MODEL = (process.env.LLM_MODEL || '').trim();

let cachedModelId = null;
let lastModelCheck = 0;
const MODEL_CACHE_TTL_MS = 60000; // 1 minute

/**
 * Discovers the active/loaded model in LM Studio via GET /v1/models.
 * Filters out embedding models and selects the primary chat model.
 *
 * @returns {Promise<string>} Discovered model ID
 */
export async function discoverActiveModel() {
  if (CONFIGURED_MODEL) {
    return CONFIGURED_MODEL;
  }

  const now = Date.now();
  if (cachedModelId && now - lastModelCheck < MODEL_CACHE_TTL_MS) {
    return cachedModelId;
  }

  try {
    const res = await axios.get(`${LLM_BASE_URL}/models`, {
      timeout: 5000,
      headers: { 'Content-Type': 'application/json' },
    });

    const models = res.data?.data || [];
    if (!Array.isArray(models) || models.length === 0) {
      throw new Error('No models found in LM Studio.');
    }

    // Filter out non-chat / embedding models
    const chatModels = models.filter(
      (m) => m.id && !m.id.toLowerCase().includes('embed')
    );

    const chosen = chatModels.length > 0 ? chatModels[0].id : models[0]?.id;
    if (!chosen) {
      throw new Error('No valid chat model ID found in LM Studio model list.');
    }

    cachedModelId = chosen;
    lastModelCheck = now;
    return chosen;
  } catch (err) {
    cachedModelId = null;
    const msg = err.response?.data?.error?.message || err.message;
    throw new Error(`LM Studio model discovery failed on ${LLM_BASE_URL}/models: ${msg}`);
  }
}

/**
 * Builds a compact, structured stock context strictly from real FinSight analysis.
 * Does NOT send raw OHLCV history or thousands of candles.
 *
 * @param {object} analysis  The raw FinSight analysis payload from /api/analysis/:ticker
 * @returns {object} Compact stock context
 */
export function buildStockContext(analysis) {
  const trend = analysis.trend || {};
  const risk = analysis.risk || {};
  const rawMetrics = risk.raw_metrics || {};
  const indicators = analysis.indicators || {};
  const explanation = analysis.explanation || {};

  const compact = {
    ticker: analysis.ticker,
    trend: {
      prediction: trend.prediction || 'UNKNOWN',
      confidence: typeof trend.confidence === 'number' ? Number(trend.confidence.toFixed(3)) : trend.confidence,
      ...(trend.probabilities ? { probabilities: trend.probabilities } : {}),
    },
    risk: {
      score: typeof risk.risk_score === 'number' ? Number(risk.risk_score.toFixed(1)) : risk.risk_score,
      category: risk.risk_level || 'UNKNOWN',
      volatility: typeof rawMetrics.annualized_volatility === 'number'
        ? Number(rawMetrics.annualized_volatility.toFixed(3))
        : rawMetrics.annualized_volatility,
      max_drawdown: typeof rawMetrics.max_drawdown === 'number'
        ? Number(rawMetrics.max_drawdown.toFixed(3))
        : rawMetrics.max_drawdown,
      downside_volatility: typeof rawMetrics.downside_volatility === 'number'
        ? Number(rawMetrics.downside_volatility.toFixed(3))
        : rawMetrics.downside_volatility,
    },
    indicators: {
      close: typeof indicators.close === 'number' ? Number(indicators.close.toFixed(2)) : indicators.close,
      rsi: typeof (indicators.rsi_14 ?? indicators.rsi) === 'number'
        ? Number((indicators.rsi_14 ?? indicators.rsi).toFixed(2))
        : (indicators.rsi_14 ?? indicators.rsi),
      macd: typeof indicators.macd === 'number' ? Number(indicators.macd.toFixed(2)) : indicators.macd,
      macd_signal: typeof indicators.macd_signal === 'number'
        ? Number(indicators.macd_signal.toFixed(2))
        : indicators.macd_signal,
      sma_50: typeof (indicators.ma_50 ?? indicators.sma_50) === 'number'
        ? Number((indicators.ma_50 ?? indicators.sma_50).toFixed(2))
        : (indicators.ma_50 ?? indicators.sma_50),
      ema_20: typeof (indicators.ema_20 ?? indicators.ma_5) === 'number'
        ? Number((indicators.ema_20 ?? indicators.ma_5).toFixed(2))
        : (indicators.ema_20 ?? indicators.ma_5),
      volatility_20: typeof indicators.volatility_20 === 'number'
        ? Number(indicators.volatility_20.toFixed(4))
        : indicators.volatility_20,
      high_low_pct: typeof indicators.high_low_pct === 'number'
        ? Number(indicators.high_low_pct.toFixed(4))
        : indicators.high_low_pct,
    },
    key_drivers: Array.isArray(explanation.key_drivers)
      ? explanation.key_drivers.slice(0, 3).map((d) => ({
          feature: d.feature,
          name: d.name || d.feature,
          value: d.value,
          importance: typeof d.importance === 'number' ? Number(d.importance.toFixed(3)) : d.importance,
          explanation: d.explanation,
        }))
      : [],
    watch_items: Array.isArray(explanation.watch_items) ? explanation.watch_items : [],
  };

  return compact;
}

/**
 * Builds the authoritative system prompt for FinSight AI stock assistant.
 *
 * @param {object} stockContext Compact structured stock context
 * @returns {string} System prompt
 */
export function buildSystemPrompt(stockContext) {
  return `You are FinSight AI, an intelligent stock-analysis assistant.

Your job is to HELP THE USER UNDERSTAND the stock being analyzed.

You are given structured data generated by FinSight's real quantitative models.

DO NOT simply repeat the supplied numbers.

INTERPRET them and explain what they mean.

When the user asks a question:
1. Understand the intent of the question.
2. Find the relevant information in the supplied stock context.
3. Explain the meaning of that information.
4. Connect related indicators when useful.
5. Give the user a clear conclusion about what the data suggests.
6. Keep the answer conversational and easy to understand.

For example:

If the user asks:
'Why is the risk high?'

Do NOT answer:
'Risk score: 68.9. Volatility: 32.5%. Drawdown: 34.5%.'

Instead answer:
'The risk is high mainly because the stock has relatively elevated volatility and a large historical drawdown. In simple terms, the stock has been experiencing larger price movements and has shown a greater potential for losses during declines.'

If the user asks:
'Explain RSI.'

Do NOT just provide:
'RSI = 42.5.'

Instead explain:
'The RSI is 42.5, which indicates that momentum is somewhat weak but the stock is not currently in the traditional oversold zone. RSI below 30 is generally considered oversold, while above 70 is considered overbought.'

If the user asks:
'Why does the model predict DOWN?'

Explain WHICH supplied model factors contribute to the prediction and what those factors mean.

If the user asks:
'What are the important factors?'

Explain the top model drivers in terms a normal investor/student can understand.

IMPORTANT:
The numbers provided by FinSight are authoritative.

You may EXPLAIN them.
You must NOT change them.

Never invent:
- prices
- indicators
- financial metrics
- model predictions
- confidence values
- risk scores
- company information

Never claim certainty about future prices.

Never give personalized buy/sell/hold instructions.

Use natural language instead of raw JSON.

DO NOT expose internal JSON structure to the user.

DO NOT say things like:
'the input contains...'
'the JSON says...'
'the context indicates...'

Speak naturally as FinSight AI.

When appropriate, use short paragraphs and simple bullet points.

Always answer the user's actual question first.

If the user asks a follow-up question such as:
'Why?'
'What does that mean?'
'Explain that.'
remember the current stock and previous conversation context.

If the supplied data is insufficient to answer something, clearly say:
'I don't have enough information in the current FinSight analysis to answer that confidently.'

Your primary goal is UNDERSTANDING, not DATA RECITATION.

==================================================
CURRENT STOCK CONTEXT (${stockContext.ticker}):
${JSON.stringify(stockContext, null, 2)}
==================================================`;
}

/**
 * Clean model output (strips internal think tags or trailing noise if present).
 *
 * @param {string} text Raw LLM content
 * @returns {string} Cleaned content
 */
function cleanModelResponse(text) {
  if (!text) return '';
  // Remove <think>...</think> blocks if produced by reasoning models
  let cleaned = text.replace(/<think>[\s\S]*?<\/think>/gi, '').trim();
  return cleaned || text.trim();
}

/**
 * Sends stock-specific prompt and conversation history to local LM Studio.
 *
 * @param {object} params
 * @param {string} params.ticker        Stock symbol (e.g. "AAPL")
 * @param {string} params.message       Current user question
 * @param {Array}  params.conversation  Prior conversation messages
 * @param {object} params.analysis      FinSight analysis object
 * @returns {Promise<object>} Result containing reply, model, and stockContext
 */
export async function getStockChatResponse({ ticker, message, conversation = [], analysis }) {
  // 1. Build compact stock context
  const stockContext = buildStockContext(analysis);

  // 2. Discover active model in LM Studio
  const modelId = await discoverActiveModel();

  // 3. Assemble message payload with system prompt + history
  const systemPrompt = buildSystemPrompt(stockContext);
  const messages = [{ role: 'system', content: systemPrompt }];

  if (Array.isArray(conversation)) {
    for (const msg of conversation) {
      if (
        msg &&
        (msg.role === 'user' || msg.role === 'assistant') &&
        typeof msg.content === 'string' &&
        msg.content.trim()
      ) {
        messages.push({
          role: msg.role,
          content: msg.content.trim(),
        });
      }
    }
  }

  // Ensure current user message is present at the end
  const lastMsg = messages[messages.length - 1];
  if (!lastMsg || lastMsg.role !== 'user' || lastMsg.content !== message.trim()) {
    messages.push({
      role: 'user',
      content: message.trim(),
    });
  }

  // 4. Send to LM Studio
  try {
    const res = await axios.post(
      `${LLM_BASE_URL}/chat/completions`,
      {
        model: modelId,
        messages,
        temperature: 0.4,
        max_tokens: 800,
      },
      {
        timeout: LLM_TIMEOUT,
        headers: { 'Content-Type': 'application/json' },
      }
    );

    const choice = res.data?.choices?.[0];
    const rawContent = choice?.message?.content || choice?.text || '';
    const cleanContent = cleanModelResponse(rawContent);

    if (!cleanContent) {
      throw new Error('Local LM Studio returned an empty response.');
    }

    return {
      ticker,
      reply: cleanContent,
      model: modelId,
      stockContext,
    };
  } catch (err) {
    if (err.code === 'ECONNREFUSED' || err.code === 'ENOTFOUND') {
      const e = new Error('Local AI is unavailable.');
      e.statusCode = 503;
      e.originalMessage = `Connection refused at ${LLM_BASE_URL}`;
      throw e;
    }
    if (err.code === 'ECONNABORTED') {
      const e = new Error('Local AI request timed out.');
      e.statusCode = 504;
      throw e;
    }
    if (err.response) {
      const detail = err.response.data?.error?.message || err.response.statusText;
      const e = new Error(`Local AI error: ${detail}`);
      e.statusCode = err.response.status || 500;
      throw e;
    }
    throw err;
  }
}
