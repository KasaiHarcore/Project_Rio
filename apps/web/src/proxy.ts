import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

/** Routes that unauthenticated users are allowed to visit. */
const PUBLIC_PATHS = new Set(['/login', '/register', '/recovery'])

export function proxy(request: NextRequest) {
  const authCookie = request.cookies.get('auth-token')
  const { pathname } = request.nextUrl

  const isPublicPath = PUBLIC_PATHS.has(pathname)

  // Unauthenticated user trying to access a protected route → redirect to login
  if (!authCookie && !isPublicPath) {
    const loginUrl = new URL('/login', request.url)
    // Preserve the original destination so we can redirect back after login
    loginUrl.searchParams.set('next', pathname)
    return NextResponse.redirect(loginUrl)
  }

  // Authenticated user trying to access auth pages → redirect to dashboard
  if (authCookie && isPublicPath) {
    return NextResponse.redirect(new URL('/', request.url))
  }

  return NextResponse.next()
}

// Run proxy on all routes EXCEPT static assets and Next.js internals
export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon\\.ico|api/|images/|css/|js/|lib/|spine/).*)'],
}
