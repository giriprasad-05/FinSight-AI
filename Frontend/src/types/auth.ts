export interface AuthUser {
  id: string;
  username: string;
  email: string;
  name: string;
}

export interface AuthResponse {
  token: string;
  expiresIn: number;
  user: AuthUser;
}
