import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
 
export function middleware(request: NextRequest) {
  // Check for the auth cookie
  const authCookie = request.cookies.get('auth-token')
  const { pathname } = request.nextUrl

  // If trying to access the dashboard (root) without auth
  if (pathname === '/' && !authCookie) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  // Optional: If already logged in and trying to access auth pages, redirect to dashboard
  if (authCookie && (pathname === '/login' || pathname === '/register')) {
    return NextResponse.redirect(new URL('/', request.url))
  }
 
  return NextResponse.next()
}
 
// Configure which paths the middleware runs on
export const config = {
  matcher: ['/', '/login', '/register'],
}
