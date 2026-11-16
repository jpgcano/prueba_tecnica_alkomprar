# Diagramas

Cada diagrama está en tres formatos, con el mismo contenido:

| Archivo | Para qué sirve |
|---|---|
| `.mmd` | El código fuente, en Mermaid. Es lo que se edita cuando el diagrama cambia |
| `.svg` | Para ver y para imprimir: no pierde nitidez al ampliar |
| `.png` | Para pegar en un documento o enviar por correo |

| Diagrama | De qué trata |
|---|---|
| `1_limpieza_de_datos` | Etapa 0: cómo se leen y se limpian los datos del Excel |
| `2_interpretacion_del_mensaje` | Etapas 1 a 5: cómo el chatbot entiende un mensaje y decide qué consulta es |

Los dos se explican en el [README del módulo](../README.md). El diagrama del agente de IA está en
la carpeta de su propio ejercicio.

Para regenerar las imágenes después de editar un `.mmd` hace falta Mermaid CLI:

```bash
npm install -g @mermaid-js/mermaid-cli
mmdc -i 1_limpieza_de_datos.mmd -o 1_limpieza_de_datos.svg -b white
mmdc -i 1_limpieza_de_datos.mmd -o 1_limpieza_de_datos.png -b white -s 2
```
