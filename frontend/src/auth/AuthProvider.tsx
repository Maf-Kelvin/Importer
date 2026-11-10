import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { authApi } from '@/api/endpoints';
import { configureApi, refreshSession, session } from '@/api/client';
import type { User } from '@/api/types';
import { AuthContext, type AuthContextValue } from './auth-context';

type State = Pick<AuthContextValue, 'status' | 'user'>;
const REFRESH_MARGIN_MS = 60_000; // refresh when less than a minute of the access token is left
const CHECK_EVERY_MS = 30_000;

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<State>({ status: 'loading', user: null });

  /** Forget everything about the session on this device. */
  const endSession = useCallback(() => {
    session.clear(false);
    queryClient.clear(); // never leave one user's cached data in memory for the next user
    setState({ status: 'anonymous', user: null });
  }, [queryClient]);

  // Any request that finds the session dead (or another tab signing out) ends it here.
  useEffect(() => {
    configureApi({ onAuthLost: endSession });
  }, [endSession]);

  // On page load: the refresh cookie (invisible to JavaScript) may still be valid.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const token = await refreshSession();
        if (!token) throw new Error('no session');
        const user: User = await authApi.me();
        if (!cancelled) setState({ status: 'authenticated', user });
      } catch {
        if (!cancelled) setState({ status: 'anonymous', user: null });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Keep the access token fresh while the app is open.
  useEffect(() => {
    if (state.status !== 'authenticated') return;
    const id = window.setInterval(() => {
      if (session.expiresAt - Date.now() < REFRESH_MARGIN_MS) {
        refreshSession()
          .then((token) => {
            if (!token) endSession();
          })
          .catch(() => undefined); // a network blip: the next request will try again
      }
    }, CHECK_EVERY_MS);
    return () => window.clearInterval(id);
  }, [state.status, endSession]);

  const login = useCallback(async (username: string, password: string) => {
    await authApi.login(username, password);
    const user = await authApi.me();
    setState({ status: 'authenticated', user });
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      /* even if the server cannot be reached, end the session on this device */
    }
    endSession();
  }, [endSession]);

  const value = useMemo<AuthContextValue>(() => ({ ...state, login, logout }), [state, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
