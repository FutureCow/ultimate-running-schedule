import createMiddleware from "next-intl/middleware";
import { routing } from "./i18n/routing";

export default createMiddleware(routing);

export const config = {
  matcher: [
    // Match all pathnames except static files, api, _next
    "/((?!api|_next/static|_next/image|favicon\\.ico|favicon\\.svg|manifest\\.json|.*\\.png|.*\\.svg).*)",
  ],
};
