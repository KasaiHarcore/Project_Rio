export interface Chunk {
  name: string
  kind: string
  startLine: number
  endLine: number
  content: string
}

/**
 * Splits a source file into logical chunks for workspace display.
 */
export function chunkFile(
  fileName: string,
  content: string
): { chunks: Chunk[]; fileTree: string } {
  const lines = content.split("\n")
  const chunkSize = 50
  const chunks: Chunk[] = []

  for (let i = 0; i < lines.length; i += chunkSize) {
    const slice = lines.slice(i, i + chunkSize)
    chunks.push({
      name: `${fileName}:${i + 1}-${Math.min(i + chunkSize, lines.length)}`,
      kind: "chunk",
      startLine: i + 1,
      endLine: Math.min(i + chunkSize, lines.length),
      content: slice.join("\n"),
    })
  }

  return { chunks, fileTree: fileName }
}
