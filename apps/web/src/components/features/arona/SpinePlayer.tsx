"use client"

import React, { useEffect, useRef } from 'react'
import { Script } from 'next/script'

interface SpinePlayerProps {
    className?: string;
    modelPath: string; // Path to .skel
    atlasPath: string; // Path to .atlas
    animation: string; // Default animation name
    scale?: number;
}

// Declare global spine variable from the script
declare global {
  interface Window {
    spine: any;
  }
}

export function SpinePlayer({ 
    className, 
    modelPath, 
    atlasPath, 
    animation = "Idle", 
    scale = 1.0 
}: SpinePlayerProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const loadedRef = useRef(false);

    useEffect(() => {
        // Only run if canvas exists and script is loaded
        if (!canvasRef.current || !window.spine || loadedRef.current) return;

        const initSpine = async () => {
             loadedRef.current = true;
             console.log(`Loading Spine Model: ${modelPath}`);
             
             try {
                 const canvas = canvasRef.current;
                 if(!canvas) return;

                 // Setup WebGL context
                 // Based on generic spine-ts documentation
                 const config = { alpha: true };
                 const gl = canvas.getContext("webgl", config) || canvas.getContext("experimental-webgl", config);
                 
                 if (!gl) {
                    console.error("WebGL cannot be initialized");
                    return;
                 }
                 
                 // Using the simpler `spine.SpineCanvas` helper if available in the bundled script, 
                 // OR implementing the manual asset manager flow.
                 // Assuming standard spine-webgl run loop pattern:

                 const spine = window.spine;
                 
                 // 1. Asset Manager
                 const assetManager = new spine.AssetManager("");
                 
                 // 2. Load Asssets
                 assetManager.loadBinary(modelPath);
                 assetManager.loadTextureAtlas(atlasPath);
                 
                 // 3. Wait for assets
                 const waitForAssets = () => {
                    if (assetManager.isLoadingComplete()) {
                        setupSkeleton(spine, assetManager, gl);
                    } else {
                        requestAnimationFrame(waitForAssets);
                    }
                 };
                 
                 requestAnimationFrame(waitForAssets);

             } catch (e) {
                 console.error("Spine failed to load:", e);
             }
        }
        
        // Short delay to ensure script has time to parse if mounting fast
        const timer = setTimeout(initSpine, 100);
        return () => clearTimeout(timer);

    }, [modelPath, atlasPath]); // Re-run if paths change

    const setupSkeleton = (spine: any, assetManager: any, gl: any) => {
         const canvas = canvasRef.current;
         if(!canvas) return;

         // Load Atlas
         const atlas = assetManager.require(atlasPath);
         // Load Skel (Binary)
         const skeletonFile = assetManager.require(modelPath);
         
         // Setup AtlasAttachmentLoader
         const atlasLoader = new spine.AtlasAttachmentLoader(atlas);
         
         // Setup SkeletonJson or SkeletonBinary
         const skeletonBinary = new spine.SkeletonBinary(atlasLoader);
         skeletonBinary.scale = scale;
         const skeletonData = skeletonBinary.readSkeletonData(skeletonFile);
         
         // Create Skeleton
         const skeleton = new spine.Skeleton(skeletonData);
         
         // Center Skeleton
         // Fix: Place it at visual center. 
         // Spine standard: (0,0) is usually at feet.
         // WebGL standard: (0,0) is center of screen if using simple Ortho.
         skeleton.x = 0; 
         skeleton.y = -600; // Move down to get the feet at bottom
         
         // Animation State
         const animationStateData = new spine.AnimationStateData(skeletonData);
         animationStateData.defaultMix = 0.2;
         const animationState = new spine.AnimationState(animationStateData);
         
         // Set Animation
         try {
            animationState.setAnimation(0, animation, true);
         } catch(e) { console.warn("Animation not found", animation)}

         // Renderer
         const renderer = new spine.SceneRenderer(canvas, gl);
         
         // Resize Logic
         const resize = () => {
             const w = canvas.clientWidth;
             const h = canvas.clientHeight;
             if (canvas.width !== w || canvas.height !== h) {
                canvas.width = w;
                canvas.height = h;
             }
             
             // Update Camera
             // Use simple Orthographic projection tailored for 2D
             // We want 0,0 to be center of screen.
             // Width/Height logic:
             if (renderer.camera) {
                 renderer.camera.position.x = 0;
                 renderer.camera.position.y = 0;
                 // Zoom out a bit -> larger view area means smaller character
                 const zoom = 1.5; 
                 renderer.camera.setOrtho(
                     -w / 2 * zoom, 
                     w / 2 * zoom, 
                     -h / 2 * zoom, 
                     h / 2 * zoom
                 );
             }
         }

         // Render Loop
         let lastTime = Date.now();
         const render = () => {
             const now = Date.now();
             const delta = (now - lastTime) / 1000;
             lastTime = now;
             
             resize();
             
             // Update
             animationState.update(delta);
             animationState.apply(skeleton);
             skeleton.updateWorldTransform();
             
             // Draw
             gl.clearColor(0, 0, 0, 0);
             gl.clear(gl.COLOR_BUFFER_BIT);
             
             renderer.begin();
             renderer.drawSkeleton(skeleton, true); // true = premultiplied alpha
             renderer.end();
             
             requestAnimationFrame(render);
         }
         
         requestAnimationFrame(render);
    }

    return (
        <>
            {/* Load the library from public/lib */}
            <script src="/lib/spine-webgl.js" onLoad={() => { console.log("Spine Lib Loaded") }} />
            
            <canvas 
                ref={canvasRef} 
                className={className} 
            />
        </>
    )
}
