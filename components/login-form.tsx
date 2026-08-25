"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { loginConSocio } from "@/app/actions/auth"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Spinner } from "@/components/ui/spinner"

export function LoginForm() {
  const router = useRouter()
  const [socio, setSocio] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    const result = await loginConSocio(socio)
    setLoading(false)

    if (!result.ok) {
      setError(result.error ?? "No se pudo iniciar sesión.")
      return
    }

    router.push("/inicio")
    router.refresh()
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <div>
        <p className="mb-2 text-center text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Acceso Socios
        </p>
        <Input
          value={socio}
          onChange={(e) => setSocio(e.target.value)}
          placeholder="Ej: 123456-01"
          aria-label="Número de socio"
          aria-invalid={!!error}
          className="h-12 text-center text-base"
          autoComplete="off"
          inputMode="numeric"
        />
        {error ? (
          <p role="alert" className="mt-2 text-center text-sm text-destructive">
            {error}
          </p>
        ) : null}
      </div>
      <Button type="submit" disabled={loading} className="h-12 text-base font-semibold tracking-wide">
        {loading ? <Spinner data-icon="inline-start" /> : null}
        INGRESAR
      </Button>
    </form>
  )
}
