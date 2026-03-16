import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'
import { parseFile } from 'music-metadata'

const CONFIG_PATH = path.join(process.cwd(), '.music-config.json')
const DEFAULT_DIR = path.join(process.cwd(), 'public', 'music')

function getMusicDir(): string {
  try {
    const raw = fs.readFileSync(CONFIG_PATH, 'utf-8')
    const config = JSON.parse(raw)
    if (config.musicDir && fs.existsSync(config.musicDir)) {
      return config.musicDir
    }
  } catch {
    // No config or invalid — use default
  }
  return DEFAULT_DIR
}

export async function GET(req: NextRequest) {
  const file = req.nextUrl.searchParams.get('file')
  if (!file) {
    return NextResponse.json({ error: 'file parameter required' }, { status: 400 })
  }

  // Prevent path traversal
  const sanitized = path.basename(file)
  const musicDir = getMusicDir()
  const filePath = path.join(musicDir, sanitized)

  if (!fs.existsSync(filePath)) {
    return NextResponse.json({ error: 'File not found' }, { status: 404 })
  }

  try {
    const metadata = await parseFile(filePath)
    const picture = metadata.common.picture?.[0]

    if (!picture) {
      return NextResponse.json({ error: 'No artwork embedded' }, { status: 404 })
    }

    return new NextResponse(Buffer.from(picture.data), {
      headers: {
        'Content-Type': picture.format,
        'Cache-Control': 'public, max-age=86400, immutable',
      },
    })
  } catch {
    return NextResponse.json({ error: 'Failed to extract artwork' }, { status: 500 })
  }
}
