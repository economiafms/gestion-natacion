import Image from "next/image"
import { redirect } from "next/navigation"
import { getSession } from "@/lib/session"
import { LoginForm } from "@/components/login-form"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"

export default async function LoginPage() {
  const session = await getSession()
  if (session) redirect("/inicio")

  return (
    <main className="flex min-h-svh flex-col items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm">
        <div
          className="mb-5 rounded-3xl border border-border px-7 py-9 text-center shadow-2xl shadow-black/40"
          style={{
            background:
              "radial-gradient(120% 140% at 50% -20%, oklch(0.55 0.22 25 / 22%) 0%, transparent 55%), linear-gradient(180deg, var(--card) 0%, var(--background) 100%)",
          }}
        >
          <span className="mb-4 inline-block rounded-full border border-gold/40 bg-gold/10 px-3.5 py-1 text-[11px] font-bold uppercase tracking-[0.14em] text-gold">
            Complejo Acuático
          </span>
          <h1 className="mt-1 text-3xl font-extrabold uppercase leading-[1.1] tracking-wide text-foreground">
            Newell&apos;s <span className="text-primary">Old Boys</span>
          </h1>
          <p className="mt-2.5 text-[15px] italic text-muted-foreground">
            &ldquo;Del deporte sos la gloria&rdquo;
          </p>

          <div className="mx-auto my-6 flex w-24 items-center justify-center">
            <Image
              src="/escudo.png"
              alt="Escudo Newell's Old Boys"
              width={96}
              height={96}
              priority
              className="h-24 w-24 object-contain"
            />
          </div>

          <LoginForm />
        </div>

        <Accordion>
          <AccordionItem value="pwa" className="rounded-2xl border border-border bg-card px-4">
            <AccordionTrigger className="text-sm font-medium">
              Instalar la app en tu celular
            </AccordionTrigger>
            <AccordionContent className="flex flex-col gap-3 text-sm leading-relaxed text-muted-foreground">
              <div>
                <p className="font-semibold text-foreground">Android (Chrome)</p>
                <p>
                  1. Tocá los tres puntos (⋮) arriba a la derecha.
                  <br />
                  2. Seleccioná &ldquo;Instalar aplicación&rdquo; o &ldquo;Agregar a la pantalla de
                  inicio&rdquo;.
                </p>
              </div>
              <div>
                <p className="font-semibold text-foreground">iPhone (Safari)</p>
                <p>
                  1. Tocá el botón Compartir (cuadrado con flecha hacia arriba).
                  <br />
                  2. Deslizá hacia abajo y tocá &ldquo;Agregar al inicio&rdquo;.
                </p>
              </div>
              <p className="text-xs">
                Tenerla instalada te permite acceder más rápido a tus tiempos, rutinas, categoría y
                seguimiento personal.
              </p>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>
    </main>
  )
}
