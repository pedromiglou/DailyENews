import { createSlice } from '@reduxjs/toolkit';

const loginSlice = createSlice({
  name: 'login',
  initialState: { loading: false, error: undefined,
                  login: undefined, password: undefined, token: undefined },
  reducers: {
    attemptLogin(state, action) {
        const { login, password } = action.payload;
        return { ...state, login, password, loading: true };
    },
    loginFailed(state, action) {
        return { ...state, loading: false, token: undefined,
                 error: action.payload.error };
    },
    tokenAcquired(state, action) {
        return { ...state, loading: false, token: action.payload.token };
    },
    tokenExpire(state, action) {
        return { ...state, loading: true, token: undefined };
    },
    logout() {
        return { loading: false, error: undefined,
                 login: undefined, password: undefined, token: undefined, };
    }
  }
});

export const { attemptLogin, loginFailed, tokenAcquired, tokenExpire, logout } = loginSlice.actions;

export default loginSlice.reducer;

export const doLogin = (
  login: string,
  password: string
): AppThunk => async dispatch => {
  try {
    dispatch(attemptLogin({ login, password }));
    const result = await getRepoDetails(login, password)
    dispatch(tokenAcquired(result))
  } catch (err) {
    dispatch(loginFailed(err.toString()))
  }
}
