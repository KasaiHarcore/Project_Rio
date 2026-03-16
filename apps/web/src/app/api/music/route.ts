import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

const AUDIO_EXTENSIONS = new Set(['.mp3', '.mp4', '.ogg', '.wav', '.m4a', '.flac', '.webm'])
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

function isDefaultDir(dir: string): boolean {
  return path.resolve(dir) === path.resolve(DEFAULT_DIR)
}

function scanDirectory(dir: string): { id: string; name: string; fileName: string; url: string }[] {
  if (!fs.existsSync(dir)) return []

  const files = fs.readdirSync(dir)
  const useDefault = isDefaultDir(dir)

  return files
    .filter(f => AUDIO_EXTENSIONS.has(path.extname(f).toLowerCase()))
    .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
    .map(fileName => {
      const ext = path.extname(fileName)
      const name = path.basename(fileName, ext)
        .replace(/[-_]/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase())

      return {
        id: Buffer.from(fileName).toString('base64url'),
        name,
        fileName,
        url: useDefault
          ? `/music/${encodeURIComponent(fileName)}`
          : `/api/music/stream?file=${encodeURIComponent(fileName)}`,
        artworkUrl: `/api/music/artwork?file=${encodeURIComponent(fileName)}`,
      }
    })
}

export async function GET() {
  const musicDir = getMusicDir()
  const tracks = scanDirectory(musicDir)
  return NextResponse.json({ tracks, musicDir })
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const { musicDir } = body

    if (!musicDir || typeof musicDir !== 'string') {
      return NextResponse.json({ error: 'musicDir is required' }, { status: 400 })
    }

    if (!fs.existsSync(musicDir)) {
      return NextResponse.json({ error: 'Directory does not exist' }, { status: 400 })
    }

    fs.writeFileSync(CONFIG_PATH, JSON.stringify({ musicDir }, null, 2))

    const tracks = scanDirectory(musicDir)
    return NextResponse.json({ tracks, musicDir })
  } catch {
    return NextResponse.json({ error: 'Invalid request' }, { status: 400 })
  }
}
