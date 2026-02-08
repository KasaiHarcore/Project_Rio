"use client"

import React, { useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@/lib/utils"

export const TracingBeam = ({
  children,
  className,
}: {
  children: React.ReactNode
  className?: string
}) => {
  return (
    <div className={cn("relative w-full", className)}>
       {children}
    </div>
  )
}

// Side Effect for the Sidebar Item: A glowing beam that scans the active item
export function ActiveBeam() {
    return (
        <motion.div
            layoutId="active-beam"
            className="absolute left-0 top-0 bottom-0 w-[3px] rounded-r-full z-20 bg-[var(--beam-color)] shadow-[0_0_10px_2px_var(--beam-glow)]"
            initial={{ opacity: 0, height: "0%" }}
            animate={{ opacity: 1, height: "100%" }}
            exit={{ opacity: 0, height: "0%" }}
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
        >
             {/* The "Scanner" head that moves up and down */}
             <motion.div 
                className="absolute top-0 w-full h-[30%] bg-gradient-to-b from-transparent via-[var(--beam-gradient)] to-white/80"
                animate={{ top: ["0%", "100%", "0%"] }}
                transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
             />
        </motion.div>
    )
}
