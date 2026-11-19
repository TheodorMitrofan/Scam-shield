export type UserRole = 'admin' | 'user';

export interface UserInfo {
  id: string;
  username: string;
  role: UserRole;
  display_name: string;
}

export interface AccountPreview {
  username: string;
  role: UserRole;
  display_name: string;
}
