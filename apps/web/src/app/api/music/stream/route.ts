import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

const CONFIG_PATH = path.join(process.cwd(), '.music-config.json')
const DEFAULT_DIR = path.join(process.cwd(), 'public', 'music')

const MIME_TYPES: Record<string, string> = {
  '.mp3': 'audio/mpeg',
  '.mp4': 'audio/mp4',
  '.ogg': 'audio/ogg',
  '.wav': 'audio/wav',
  '.m4a': 'audio/mp4',
  '.flac': 'audio/flac',
  '.webm': 'audio/webm',
}

function getMusicDir(): string {
  try {
    const raw = fs.readFileSync(CONFIG_PATH, 'utf-8')
    const config = JSON.parse(raw)
    if (config.musicDir && fs.existsSync(config.musicDir)) {
      return config.musicDir
    }
  } catch {
    // fallback
  }
  return DEFAULT_DIR
}

export async function GET(req: NextRequest) {
  const fileName = req.nextUrl.searchParams.get('file')
  if (!fileName) {
    return NextResponse.json({ error: 'file parameter required' }, { status: 400 })
  }

  // Prevent path traversal
  const sanitized = path.basename(fileName)
  const musicDir = getMusicDir()
  const filePath = path.join(musicDir, sanitized)

  if (!fs.existsSync(filePath)) {
    return NextResponse.json({ error: 'File not found' }, { status: 404 })
  }

  const stat = fs.statSync(filePath)
  const ext = path.extname(sanitized).toLowerCase()
  const contentType = MIME_TYPES[ext] || 'application/octet-stream'

  const rangeHeader = req.headers.get('range')

  if (rangeHeader) {
    const match = rangeHeader.match(/bytes=(\d+)-(\d*)/)
    if (match) {
      const start = parseInt(match[1], 10)
      const end = match[2] ? parseInt(match[2], 10) : stat.size - 1
      const chunkSize = end - start + 1

      const stream = fs.createReadStream(filePath, { start, end })
      const readable = new ReadableStream({
        start(controller) {
          stream.on('data', (chunk: Buffer | string) => controller.enqueue(typeof chunk === 'string' ? Buffer.from(chunk) : chunk))
          stream.on('end', () => controller.close())
          stream.on('error', (err) => controller.error(err))
        },
      })

      return new NextResponse(readable, {
        status: 206,
        headers: {
          'Content-Type': contentType,
          'Content-Range': `bytes ${start}-${end}/${stat.size}`,
          'Content-Length': String(chunkSize),
          'Accept-Ranges': 'bytes',
        },
      })
    }
  }

  // Full file response
  const stream = fs.createReadStream(filePath)
  const readable = new ReadableStream({
    start(controller) {
      stream.on('data', (chunk: Buffer | string) => controller.enqueue(typeof chunk === 'string' ? Buffer.from(chunk) : chunk))
      stream.on('end', () => controller.close())
      stream.on('error', (err) => controller.error(err))
    },
  })

  return new NextResponse(readable, {
    status: 200,
    headers: {
      'Content-Type': contentType,
      'Content-Length': String(stat.size),
      'Accept-Ranges': 'bytes',
    },
  })
}
