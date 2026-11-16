# Supuestos y decisiones

El enunciado deja varios puntos abiertos y los datos traen errores. Esta tabla registra cada decisión y su
justificación. Criterio general: **no destruir la integridad de los datos**. Se corrige la forma, no el contenido.

## Sobre las consultas

| # | Situación | Decisión | Justificación |
|---|---|---|---|
| 1 | Qué es "mayor descuento" | Se ordena por porcentaje | Permite comparar productos de precios muy distintos |
| 2 | Fórmula | `(original − descuento) / original × 100` | Definición estándar |
| 3 | Un producto tiene precio en varios comercios | La consulta por EAN muestra todos los pares, con comercio y vendedor | Cada comercio maneja sus precios; ocultar alguno sería perder información |
| 4 | Rankings y resúmenes | Una entrada por producto, con su mejor descuento y el comercio que lo ofrece | El enunciado pide "los n productos"; así no se repiten |
| 5 | Top sin cantidad | 10 por defecto, máximo 50 | Una respuesta de chat debe poder leerse |
| 6 | "Superiores a X %" con muchos resultados | Total, los 20 mayores y descarga completa en CSV | Con 30 % salen 2.862 productos |
| 7 | "Superior a" | Estrictamente mayor que X | Es lo que significa "superior" |
| 8 | Consulta por almacén o zona | Cantidad de productos, cuántos tienen descuento, promedio y los 5 mayores. La zona agrega un desglose por almacén | Resume "los descuentos de un lugar" en una sola respuesta |
| 9 | Promedio | Solo sobre productos con descuento; se informa cuántos no tienen | Mezclar los que no tienen descuento distorsiona el promedio |

| 10a | "Menos de X %" o "entre X y Y %" | Se responden como tope máximo y como rango (el rango incluye los extremos) | Responder "superior a" cuando el usuario pidió "menos de" sería un dato equivocado |
| 10b | El usuario nombra un producto sin EAN ("cuánto vale un televisor samsung") | Se busca por nombre, marca y categoría, y se muestran los productos con precio, descuento y EAN | Un usuario nuevo no conoce los EAN |
| 10c | Palabras de producto dentro de otra consulta ("top 5 celulares") | Se usan como filtro. Si no coinciden con nada, se avisa y se muestra el resultado general | Ignorar "celulares" en silencio daría una respuesta que parece correcta y no lo es |
| 10d | Qué precio se muestra al buscar por nombre | El de su mejor descuento; si no tiene descuento, su precio original más bajo | Es la misma regla de los rankings |

## Sobre los datos

| # | Situación | Casos | Decisión | Justificación |
|---|---|---|---|---|
| 10 | Precio guardado como texto (`'4399000.0'`) | 4.575 celdas | Se convierte a número | Es formato, no contenido |
| 11 | Mensaje de error en lugar de precio | 27 celdas | Se trata como sin dato | No es un precio |
| 12 | Precio en 0 | 28 celdas | Se trata como sin dato | Un producto no se vende a cero pesos |
| 13 | Sin precio con descuento, o igual al original | 3.790 pares | Estado "sin descuento"; se muestra solo el precio original | El diccionario marca ese campo como opcional |
| 14 | Precio con descuento mayor que el original | 4 pares | Estado "precio inconsistente": se muestra el precio original y queda fuera de rankings | No es un descuento, es un error del dato |
| 15 | Hay precio con descuento pero no precio original | 161 pares | Estado "precio no válido": no se muestra ningún valor y queda fuera de rankings | Mostrar el precio rebajado como si fuera el normal informaría un valor falso |
| 16 | EAN repetido | 15 EAN, 30 filas | Se conservan ambos y se marcan como ambiguos. El bot muestra los dos; el almacén sirve de filtro opcional | En los 15 casos son productos distintos. Borrar uno sería arbitrario |
| 17 | EAN con un espacio en medio | 20 | Se quita el espacio, en los datos y en lo que escribe el usuario | Es formato |
| 18 | `ALM-012` aparece dos veces en la hoja de zonas y `ALM-013` no existe | 1 fila | La fila de `Almacen_13` se corrige a `ALM-013` | Las otras 19 filas cumplen el patrón número = número. Hay 322 productos en ALM-013. Ambas filas son de Zona_3, así que no hay riesgo de asignar mal la zona |
| 19 | Producto sin almacén | 12 | Queda fuera de las consultas por almacén y zona. Sí aparece por EAN y en rankings generales | No se adivina la ubicación |
| 20 | Espacios dobles, al borde o "no separables" en textos | 460 celdas | Se limpian | No cambia el significado |
| 21 | Mayúsculas y tildes distintas (`KALLEY` / `Kalley`) | — | Se muestra el original; para buscar se usa una columna normalizada | No se decide cuál es "la correcta" |
| 22 | Carácter `\|` en nombres de producto | 166 | No se toca | Parece intencional ("Adaptador\|Cargador"); cambiarlo sería inventar |
| 23 | Precios o descuentos muy altos | — | No se tocan | Los datos son ficticios; un valor llamativo no es evidencia de error |

| 10e | Palabra mal escrita ("nebera", "sansung") | Se corrige contra las palabras que existen en los datos, solo si el parecido supera 0,82, y se avisa | Un usuario escribe rápido; corregir en silencio sería peor que avisar |
| 10f | Marca que no existe en los datos ("celular nokia") | Se descarta esa palabra, se responde con el resto ("celular") y se avisa | Devolver cero resultados sin explicación parece un error del sistema |
| 10g | Mensaje sin producto después de uno que sí lo tenía ("¿cuál es la más barata?") | Se mantiene el último producto nombrado y se avisa; «todos» quita el filtro | Es como hablaría una persona; el aviso evita confusión |

## Sobre la interfaz

| # | Situación | Decisión | Justificación |
|---|---|---|---|
| 24 | Canal | Web con Streamlit | Se ejecuta en local sin cuentas ni claves y muestra tablas reales |
| 25 | Entrada | Híbrida: texto libre y botones que envían frases estándar | Toda entrada pasa por el mismo intérprete de reglas, que es lo que pide el enunciado |
| 26 | Falta un dato | El bot lo pide y recuerda la consulta pendiente | Evita que el usuario repita la pregunta completa |
