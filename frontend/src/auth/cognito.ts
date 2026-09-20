import {
  AuthenticationDetails,
  CognitoUser,
  CognitoUserPool,
} from 'amazon-cognito-identity-js'

const USER_POOL_ID = import.meta.env.VITE_COGNITO_USER_POOL_ID
const CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID

if (!USER_POOL_ID || !CLIENT_ID) {
  throw new Error(
    'Cognito env vars are not set — copy .env.example to .env and fill them in',
  )
}

const userPool = new CognitoUserPool({
  UserPoolId: USER_POOL_ID,
  ClientId: CLIENT_ID,
})

export type Role = 'ComplianceOfficer' | 'Subcontractor' | 'Unknown'

export interface Session {
  email: string
  role: Role
  /** Set only for subcontractor logins: the record this user may act on. */
  subcontractorId: string | null
}

function sessionFromClaims(claims: Record<string, unknown>): Session {
  const groups = (claims['cognito:groups'] as string[] | undefined) ?? []
  const role: Role = groups.includes('ComplianceOfficer')
    ? 'ComplianceOfficer'
    : groups.includes('Subcontractor')
      ? 'Subcontractor'
      : 'Unknown'

  return {
    email: (claims.email as string) ?? '',
    role,
    subcontractorId: (claims['custom:subcontractorId'] as string) ?? null,
  }
}

export function signIn(email: string, password: string): Promise<Session> {
  const user = new CognitoUser({ Username: email, Pool: userPool })
  const credentials = new AuthenticationDetails({
    Username: email,
    Password: password,
  })

  return new Promise((resolve, reject) => {
    user.authenticateUser(credentials, {
      onSuccess: (result) =>
        resolve(sessionFromClaims(result.getIdToken().decodePayload())),
      onFailure: (err) =>
        reject(new Error(err?.message ?? 'Could not sign in')),
      newPasswordRequired: () =>
        reject(
          new Error(
            'This account needs a new password. An administrator must reset it.',
          ),
        ),
    })
  })
}

export function signOut() {
  userPool.getCurrentUser()?.signOut()
}

/** Resolves the current session, refreshing the token if it has expired.
 *  Returns null when nobody is signed in or the refresh token has lapsed. */
export function getSession(): Promise<Session | null> {
  const user = userPool.getCurrentUser()
  if (!user) return Promise.resolve(null)

  return new Promise((resolve) => {
    user.getSession((err: Error | null, session: any) => {
      if (err || !session?.isValid()) return resolve(null)
      resolve(sessionFromClaims(session.getIdToken().decodePayload()))
    })
  })
}

/** The raw JWT for the Authorization header. Cognito refreshes it here if
 *  needed, so callers never have to think about expiry. */
export function getIdToken(): Promise<string | null> {
  const user = userPool.getCurrentUser()
  if (!user) return Promise.resolve(null)

  return new Promise((resolve) => {
    user.getSession((err: Error | null, session: any) => {
      if (err || !session?.isValid()) return resolve(null)
      resolve(session.getIdToken().getJwtToken())
    })
  })
}
