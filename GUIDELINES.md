# Directrices del mensaje

Los avisos los lee una persona en el móvil, muchas veces sin la terminal delante.
Un mensaje = una tarea terminada (o bloqueada). Nada de pings de progreso salvo
que se pidan.

## Forma

```
✅ turtletrips 1.7.0 desplegado
📁 turtletrips · 🖥️ ginnugagap

Imagen ghcr.io/zurdi15/turtletrips:1.7.0 desplegada en el clúster.
Argo: turtletrips Synced/Healthy. Health: HTTP 200.

Novedades 1.7.0:
- Moneda secundaria por viaje (p. ej. VND), elegible junto a la base en el formulario del viaje.
- En el gasto, la moneda se elige con principal · secundaria · otra.
- En tabla y lista de gastos manda lo pagado en su moneda; la conversión a la base va en pequeño debajo.
```

1. **Titular** (`-t`): icono de estado + `proyecto versión verbo`. Corto, en
   pasado, sin punto final: `turtletrips 1.7.0 desplegado`, `Tests rotos en
   bifrost`, `Migración de immich terminada`. El icono lo pone `-s`:
   `ok` ✅ · `fail` ❌ · `warn` ⚠️ · `info` ℹ️ · `ask` ❓.
2. **Contexto** (automático): `📁 proyecto · 🖥️ host`. El proyecto sale del
   repo git; el host es la máquina donde corre el comando. Si lo que importa es
   el destino (un despliegue), pásalo con `-H ginnugagap`.
3. **Cuerpo**, separado por una línea en blanco, en este orden:
   - **Qué se ha hecho**, en una o dos frases con los identificadores que
     permiten comprobarlo (imagen, tag, commit, ruta).
   - **Cómo se ha verificado**: estado de Argo, código HTTP, tests en verde…
     Si algo no se pudo verificar, se dice.
   - **Novedades** (solo en releases): `Novedades X.Y.Z:` y una lista `-` con
     una línea por cambio, contada para quien usa la app, no para quien lee el
     código.
   - **Siguiente paso** si lo hay, o la pregunta concreta si el estado es `ask`.

## Reglas

- En español, salvo que el usuario escriba en otro idioma.
- Texto plano: sin Markdown, sin HTML, sin bloques de código. Telegram lo
  enseñaría literal.
- Autocontenido: quien lo lee no ve la terminal. Nada de "ver arriba" ni ids de
  mensajes.
- Corto: cabe en una pantalla de móvil. El tope duro son 4096 caracteres y a
  partir de ahí se trunca.
- Sin secretos: ni tokens, ni claves, ni contenido completo de ficheros.
- `fail` lleva el error exacto (una línea) y dónde: `npm run build: TS2345 en
  src/api/client.ts:88`.
- Salida `0` = entregado. Si falla, el motivo va por stderr: se le dice al
  usuario en la terminal, no se reintenta en bucle.
