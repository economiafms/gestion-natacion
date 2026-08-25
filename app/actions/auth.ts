"use server"

import { db } from "@/lib/db"
import { nadadores, usuarios } from "@/lib/db/schema"
import { createSession, destroySession, getSession } from "@/lib/session"
import { eq } from "drizzle-orm"
import { redirect } from "next/navigation"

export type LoginResult = {
  ok: boolean
  error?: string
  nombre?: string
}

export async function loginConSocio(rawInput: string): Promise<LoginResult> {
  const socioLimpio = rawInput.split("-")[0].trim()

  if (!socioLimpio) {
    return { ok: false, error: "Ingresá un número de socio." }
  }

  const [usuario] = await db
    .select()
    .from(usuarios)
    .where(eq(usuarios.nrosocio, socioLimpio))
    .limit(1)

  if (!usuario) {
    return { ok: false, error: "Número de socio no registrado." }
  }

  const [nadador] = await db
    .select()
    .from(nadadores)
    .where(eq(nadadores.nrosocio, socioLimpio))
    .limit(1)

  if (!nadador) {
    return { ok: false, error: "Socio válido pero sin ficha de nadador activa." }
  }

  await createSession({
    codnadador: nadador.codnadador,
    nrosocio: socioLimpio,
    nombre: nadador.nombre,
    apellido: nadador.apellido,
    perfil: usuario.perfil as "N" | "M" | "P",
  })

  return { ok: true, nombre: nadador.nombre }
}

export async function cerrarSesion() {
  await destroySession()
  redirect("/")
}

export async function requireSession() {
  const session = await getSession()
  if (!session) redirect("/")
  return session
}
