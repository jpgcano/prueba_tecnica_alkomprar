# Diagramas

Cada diagrama está en tres formatos, con el mismo contenido:

| Archivo | Para qué sirve |
|---|---|
| `.mmd` | El código fuente, en Mermaid. Es lo que se edita cuando el diagrama cambia |
| `.svg` | Para ver y para imprimir: no pierde nitidez al ampliar |
| `.png` | Para pegar en un documento o enviar por correo |

| Diagrama | De qué trata |
|---|---|
| `arquitectura` | Cómo funciona el agente: canal, filtros, modelo, herramientas y escalamiento |

Se explica en el [README del ejercicio](../README.md).

Para regenerar las imágenes después de editar el `.mmd` hace falta Mermaid CLI:

```bash
npm install -g @mermaid-js/mermaid-cli
mmdc -i arquitectura.mmd -o arquitectura.svg -b white
mmdc -i arquitectura.mmd -o arquitectura.png -b white -s 2
```
