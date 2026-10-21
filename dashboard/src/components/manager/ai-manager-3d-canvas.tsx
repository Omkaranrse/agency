'use client';

import * as React from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import { clone as skeletonClone } from 'three/examples/jsm/utils/SkeletonUtils.js';
import type { AvatarState } from './ai-manager-avatar';

interface CatModelProps {
  state: AvatarState;
  reducedMotion: boolean;
}

function CatCharacterModel({ state, reducedMotion }: CatModelProps) {
  const groupRef = React.useRef<THREE.Group>(null);
  const gltf = useGLTF('/models/ai-manager-cat.glb');

  // Clone scene with skeleton utilities so materials and bones remain isolated
  const clonedScene = React.useMemo(() => {
    return skeletonClone(gltf.scene);
  }, [gltf.scene]);

  // Set up animation mixer and clip actions
  const mixerRef = React.useRef<THREE.AnimationMixer | null>(null);
  const actionsRef = React.useRef<Record<string, THREE.AnimationAction>>({});
  const activeActionRef = React.useRef<THREE.AnimationAction | null>(null);

  React.useEffect(() => {
    if (!clonedScene) return;

    const mixer = new THREE.AnimationMixer(clonedScene);
    mixerRef.current = mixer;

    const actions: Record<string, THREE.AnimationAction> = {};
    gltf.animations.forEach((clip) => {
      const action = mixer.clipAction(clip);
      actions[clip.name] = action;
    });
    actionsRef.current = actions;

    // Default to idle
    const defaultClip = actions['idle'] || Object.values(actions)[0];
    if (defaultClip) {
      defaultClip.reset().fadeIn(0.2).play();
      activeActionRef.current = defaultClip;
    }

    return () => {
      mixer.stopAllAction();
    };
  }, [clonedScene, gltf.animations]);

  // Cross-fade animation clip based on incoming state
  React.useEffect(() => {
    if (reducedMotion) {
      // If user prefers reduced motion, pause animations
      if (mixerRef.current) {
        mixerRef.current.timeScale = 0;
      }
      return;
    } else if (mixerRef.current) {
      mixerRef.current.timeScale = 1;
    }

    const actions = actionsRef.current;
    if (!actions) return;

    // Map avatar state to available embedded GLB clips
    let targetClipName = 'idle';
    switch (state) {
      case 'listening':
        targetClipName = 'listening';
        break;
      case 'thinking':
        targetClipName = 'thinking';
        break;
      case 'speaking':
        targetClipName = 'speaking';
        break;
      case 'success':
        targetClipName = 'success';
        break;
      case 'warning':
        targetClipName = 'thinking'; // attentive analysis
        break;
      case 'error':
        targetClipName = 'error';
        break;
      default:
        targetClipName = 'idle';
    }

    const targetAction = actions[targetClipName] || actions['idle'];
    if (!targetAction) return;

    if (activeActionRef.current !== targetAction) {
      const prevAction = activeActionRef.current;
      targetAction.reset();

      if (prevAction) {
        prevAction.fadeOut(0.35);
        targetAction.fadeIn(0.35).play();
      } else {
        targetAction.play();
      }

      activeActionRef.current = targetAction;
    }
  }, [state, reducedMotion]);

  // Frame loop: update mixer and add subtle pointer tracking to head
  const { pointer } = useThree();
  useFrame((_, delta) => {
    if (mixerRef.current && !reducedMotion) {
      mixerRef.current.update(delta);
    }

    // Subtle head tracking towards pointer when idle or listening
    if (!reducedMotion && clonedScene && (state === 'idle' || state === 'listening')) {
      const head = clonedScene.getObjectByName('Head');
      if (head) {
        // Softly blend pointer offset into head rotation
        const targetX = pointer.y * -0.08;
        const targetY = pointer.x * 0.15;
        head.rotation.x = THREE.MathUtils.lerp(head.rotation.x, targetX, 0.05);
        head.rotation.y = THREE.MathUtils.lerp(head.rotation.y, targetY, 0.05);
      }
    }
  });

  return (
    <group ref={groupRef} position={[0, -0.65, 0]}>
      <primitive object={clonedScene} />

      {/* Modern Circular Platform Pedestal */}
      <mesh position={[0, -0.02, 0]} receiveShadow>
        <cylinderGeometry args={[0.75, 0.85, 0.04, 32]} />
        <meshStandardMaterial color="#121925" roughness={0.4} metalness={0.6} />
      </mesh>

      {/* Glowing Neon Ring on Pedestal Rim */}
      <mesh position={[0, -0.01, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.72, 0.75, 32]} />
        <meshBasicMaterial
          color={
            state === 'speaking'
              ? '#40E0C0'
              : state === 'listening'
              ? '#8B8BFF'
              : state === 'error'
              ? '#EF4444'
              : state === 'warning'
              ? '#F59E0B'
              : state === 'success'
              ? '#10B981'
              : '#40E0C0'
          }
          transparent
          opacity={0.8}
        />
      </mesh>

      {/* Subtle Contact Shadow */}
      <mesh position={[0, -0.03, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[0.95, 32]} />
        <meshBasicMaterial color="#05070B" transparent opacity={0.6} />
      </mesh>
    </group>
  );
}

// Pre-load GLB so switching is instant
useGLTF.preload('/models/ai-manager-cat.glb');

export interface AIManager3DCanvasProps {
  state?: AvatarState;
  reducedMotion?: boolean;
  orbitControlsRef?: React.MutableRefObject<any>;
}

export default function AIManager3DCanvas({
  state = 'idle',
  reducedMotion = false,
  orbitControlsRef,
}: AIManager3DCanvasProps) {
  return (
    <Canvas
      camera={{ position: [0, 0.45, 1.85], fov: 42 }}
      shadows
      gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
      className="w-full h-full cursor-grab active:cursor-grabbing"
    >
      {/* Dynamic Lighting Setup */}
      <ambientLight color="#1E293B" intensity={1.1} />

      {/* Key Warm Executive Light */}
      <directionalLight
        position={[2.5, 4.0, 3.0]}
        intensity={1.6}
        color="#F8FAFC"
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
        shadow-bias={-0.0001}
      />

      {/* Soft Teal Agency Accent Fill Light */}
      <directionalLight
        position={[-3.0, 2.0, 1.5]}
        intensity={0.65}
        color="#40E0C0"
      />

      {/* Soft Violet Rim Light for Gray Fur Silhouette */}
      <directionalLight
        position={[0, 2.8, -2.5]}
        intensity={1.3}
        color="#8B8BFF"
      />

      {/* Subtle Under-Pedestal Uplight */}
      <pointLight position={[0, -0.4, 0.5]} intensity={0.5} color="#40E0C0" distance={2} />

      {/* 3D Cat Mascot Model */}
      <React.Suspense fallback={null}>
        <CatCharacterModel state={state} reducedMotion={reducedMotion} />
      </React.Suspense>

      {/* Constrained Orbit Controls */}
      <OrbitControls
        ref={orbitControlsRef}
        enablePan={false}
        enableZoom={true}
        minDistance={1.3}
        maxDistance={2.6}
        minPolarAngle={Math.PI / 3.8}
        maxPolarAngle={Math.PI / 1.95}
        minAzimuthAngle={-Math.PI / 2.8}
        maxAzimuthAngle={Math.PI / 2.8}
        enableDamping
        dampingFactor={0.08}
        target={[0, 0.28, 0]}
      />
    </Canvas>
  );
}
