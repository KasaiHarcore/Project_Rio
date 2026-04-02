"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[ErrorBoundary]", error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0d1117] px-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="w-full max-w-md space-y-6 text-center"
      >
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full border border-rose-900/20 bg-rose-600/10">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-7 w-7 text-rose-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
            />
          </svg>
        </div>

        <h1 className="text-xl font-semibold text-neutral-200">
          Something went wrong
        </h1>

        <p className="text-sm leading-relaxed text-neutral-400">
          {error.message || "An unexpected error occurred."}
        </p>

        <div className="flex items-center justify-center gap-3 pt-2">
          <button
            onClick={reset}
            className="rounded-lg bg-rose-600 px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-rose-700 focus:outline-none focus:ring-2 focus:ring-rose-500/40"
          >
            Try again
          </button>
          <Link
            href="/"
            className="rounded-lg border border-neutral-700 px-5 py-2 text-sm font-medium text-neutral-300 transition-colors hover:border-neutral-600 hover:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-neutral-500/40"
          >
            Go home
          </Link>
        </div>
      </motion.div>
    </div>
  );
}
