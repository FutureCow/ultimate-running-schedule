import createMiddleware from "next-intl/middleware";
import { routing } from "./i18n/routing";

export default createMiddleware(routing);

export const config = {
  matcher: [
    // Only run locale middleware on page routes — skip api, _next, .well-known,
    // and any path whose last segment contains a dot (static files like sw.js, *.png, etc.)
    "/((?!api|_next|_vercel|\\.well-known|[^/]+\\.[^/]+$).*)",
  ],
};
