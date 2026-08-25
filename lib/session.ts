import "server-only"
import { SignJWT, jwtVerify } from "jose"
import { cookies } from "next/headers"

const COOKIE_NAME = "nob_session"
const ONE_WEEK = 60 * 60 * 24 * 7

function getSecret() {
  const secret = process.env.SESSION_SECRET
  if (!secret) {
    throw new Error("SESSION_SECRET is not set")
  }
  return new TextEncoder().encode(secret)
}

export type SessionPayload = {
  codnadador: number
  nrosocio: string
  nombre: string
  apellido: string
  perfil: "N" | "M" | "P"
}

export async function createSession(payload: SessionPayload) {
  const token = await new SignJWT({ ...payload })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime(`${ONE_WEEK}s`)
    .sign(getSecret())

  const cookieStore = await cookies()
  cookieStore.set(COOKIE_NAME, token, {
    httpOnly: true,
    secure: true,
    sameSite: "none",
    path: "/",
    maxAge: ONE_WEEK,
  })
}

export async function getSession(): Promise<SessionPayload | null> {
  const cookieStore = await cookies()
  const token = cookieStore.get(COOKIE_NAME)?.value
  if (!token) return null

  try {
    const { payload } = await jwtVerify(token, getSecret())
    return payload as unknown as SessionPayload
  } catch {
    return null
  }
}

export async function destroySession() {
  const cookieStore = await cookies()
  cookieStore.delete(COOKIE_NAME)
}
