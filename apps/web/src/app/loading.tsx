export default function Loading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0d1117]">
      <div className="flex items-center gap-2">
        <span className="h-2 w-2 animate-[pulse-dot_1.4s_ease-in-out_infinite] rounded-full bg-rose-500" />
        <span className="h-2 w-2 animate-[pulse-dot_1.4s_ease-in-out_0.2s_infinite] rounded-full bg-rose-500" />
        <span className="h-2 w-2 animate-[pulse-dot_1.4s_ease-in-out_0.4s_infinite] rounded-full bg-rose-500" />
      </div>

      <style>{`
        @keyframes pulse-dot {
          0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
          40% { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </div>
  );
}
