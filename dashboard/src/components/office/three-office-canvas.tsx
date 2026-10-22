'use client';

import * as React from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Text, useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import { clone as skeletonClone } from 'three/examples/jsm/utils/SkeletonUtils.js';
import type { AgentRole, OfficeEmployeeState, WorkstationState } from '@/features/office/types';
import { RotateCcw } from 'lucide-react';

/* ─────────────── COLOR PALETTE ─────────────── */
const PALETTE = {
  floor: '#C4A882',       // warm oak
  floorTile: '#B89B72',   // alternate tile
  wall: '#E8DDD0',        // cream wall
  wallAccent: '#D4C5B3',  // wall trim
  desk: '#8B6B4A',        // dark wood desk
  deskTop: '#A0805E',     // desk surface
  monitor: '#1A1A2E',     // monitor bezel
  monitorScreen: '#16213E',
  chair: '#4A4A5A',       // chair base
  plant: '#5B8C5A',       // plant green
  pot: '#B8754A',         // terracotta pot
  bookshelf: '#7A5C3E',   // bookshelf wood
  lamp: '#F4D03F',        // lamp glow
  carpet: '#6B5B73',      // subtle carpet
  window: '#87CEEB',      // sky blue window
  windowFrame: '#E8DDD0',
};

/* ─────────────── CHARACTER SKINS ─────────────── */
interface CharacterSkin {
  role: AgentRole;
  name: string;
  skinTone: string;
  hairColor: string;
  shirtColor: string;
  pantsColor: string;
  shoeColor: string;
  accessoryColor: string;
  eyeColor: string;
  hasGlasses?: boolean;
  hasHeadset?: boolean;
  hasHat?: boolean;
  hatColor?: string;
}

const CHARACTER_SKINS: Record<AgentRole, CharacterSkin> = {
  manager: {
    role: 'manager',
    name: 'Manager',
    skinTone: '#E8B88A',
    hairColor: '#2C1810',
    shirtColor: '#1E3A5F',  // navy suit
    pantsColor: '#1A1A2E',
    shoeColor: '#2C1810',
    accessoryColor: '#C0A060', // gold tie
    eyeColor: '#2C3E50',
    hasHeadset: true,
  },
  pm: {
    role: 'pm',
    name: 'PM',
    skinTone: '#D4A574',
    hairColor: '#8B4513',
    shirtColor: '#4A90D9',  // blue polo
    pantsColor: '#3D3D5C',
    shoeColor: '#333333',
    accessoryColor: '#F5F5DC', // clipboard white
    eyeColor: '#4A6741',
    hasGlasses: true,
  },
  designer: {
    role: 'designer',
    name: 'Designer',
    skinTone: '#F0C8A0',
    hairColor: '#C75B8E',   // creative pink/purple
    shirtColor: '#9B59B6',  // purple creative
    pantsColor: '#2C3E50',
    shoeColor: '#E74C3C',
    accessoryColor: '#F39C12', // design pen gold
    eyeColor: '#2980B9',
  },
  builder: {
    role: 'builder',
    name: 'Builder',
    skinTone: '#C8956C',
    hairColor: '#1A1A1A',
    shirtColor: '#2ECC71',  // green hoodie
    pantsColor: '#34495E',
    shoeColor: '#7F8C8D',
    accessoryColor: '#3498DB', // laptop blue
    eyeColor: '#27AE60',
  },
  qa: {
    role: 'qa',
    name: 'QA',
    skinTone: '#E8C4A0',
    hairColor: '#D4A052',   // blonde
    shirtColor: '#E67E22',  // orange
    pantsColor: '#2C3E50',
    shoeColor: '#333333',
    accessoryColor: '#E74C3C', // red magnifying glass
    eyeColor: '#8B4513',
    hasGlasses: true,
  },
  reviewer: {
    role: 'reviewer',
    name: 'Reviewer',
    skinTone: '#D4A574',
    hairColor: '#696969',   // silver/gray
    shirtColor: '#7D3C98',  // deep purple
    pantsColor: '#1A1A2E',
    shoeColor: '#2C1810',
    accessoryColor: '#27AE60', // approval green badge
    eyeColor: '#34495E',
  },
  devops: {
    role: 'devops',
    name: 'DevOps',
    skinTone: '#E0B088',
    hairColor: '#2C1810',
    shirtColor: '#2C3E50',  // dark tech shirt
    pantsColor: '#1A1A1A',
    shoeColor: '#333333',
    accessoryColor: '#00CED1', // cyan infrastructure
    eyeColor: '#1ABC9C',
    hasHat: true,
    hatColor: '#2C3E50',
  },
};

/* ─────────────── STATION LAYOUT ─────────────── */
interface StationConfig {
  role: AgentRole;
  name: string;
  position: [number, number, number];
  rotation?: number; // Y-axis rotation in radians
}

const STATIONS: StationConfig[] = [
  { role: 'manager', name: 'Manager', position: [0, 0, -3.5], rotation: 0 },
  { role: 'pm', name: 'Planning', position: [-4, 0, -1], rotation: Math.PI / 6 },
  { role: 'designer', name: 'Design Studio', position: [-4, 0, 2.5], rotation: Math.PI / 4 },
  { role: 'builder', name: 'Dev Terminal', position: [0, 0, 1], rotation: 0 },
  { role: 'qa', name: 'QA Lab', position: [4, 0, -1], rotation: -Math.PI / 6 },
  { role: 'reviewer', name: 'Review Desk', position: [4, 0, 2.5], rotation: -Math.PI / 4 },
  { role: 'devops', name: 'Cloud Ops', position: [0, 0, 4.5], rotation: Math.PI },
];

/* ─────────────── STATUS COLORS ─────────────── */
function getStatusColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'busy': case 'working': case 'building':
    case 'running': case 'in_progress':
      return '#2ECC71';
    case 'blocked': case 'awaiting_approval': case 'waiting_approval':
      return '#F39C12';
    case 'failed':
      return '#E74C3C';
    case 'completed': case 'ready':
      return '#27AE60';
    case 'reviewing':
      return '#9B59B6';
    default:
      return '#3498DB';
  }
}

function getStatusLabel(status: string): string {
  switch (status.toLowerCase()) {
    case 'busy': case 'working': case 'in_progress': return 'WORKING';
    case 'building': return 'BUILDING';
    case 'running': return 'RUNNING';
    case 'blocked': return 'BLOCKED';
    case 'awaiting_approval': case 'waiting_approval': return 'APPROVAL';
    case 'failed': return 'FAILED';
    case 'completed': case 'ready': return 'DONE';
    case 'reviewing': return 'REVIEWING';
    case 'walking': return 'MOVING';
    default: return 'IDLE';
  }
}

/* ═══════════════ MINECRAFT VOXEL CHARACTER ═══════════════ */
function MinecraftCharacter({
  skin,
  status,
  isSelected,
  onClick,
  position,
}: {
  skin: CharacterSkin;
  status: string;
  isSelected: boolean;
  onClick: () => void;
  position: [number, number, number];
}) {
  const groupRef = React.useRef<THREE.Group>(null);
  const rightArmRef = React.useRef<THREE.Group>(null);
  const leftArmRef = React.useRef<THREE.Group>(null);
  const rightLegRef = React.useRef<THREE.Group>(null);
  const leftLegRef = React.useRef<THREE.Group>(null);
  const headRef = React.useRef<THREE.Group>(null);

  const isBusy = ['busy', 'working', 'running', 'building', 'in_progress', 'reviewing'].includes(
    status.toLowerCase()
  );
  const isBlocked = ['blocked', 'failed'].includes(status.toLowerCase());
  const isWaiting = ['awaiting_approval', 'waiting_approval'].includes(status.toLowerCase());

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();

    if (isBusy) {
      // Typing animation: arms swing slightly, head bobs
      if (rightArmRef.current) {
        rightArmRef.current.rotation.x = Math.sin(t * 8) * 0.35;
      }
      if (leftArmRef.current) {
        leftArmRef.current.rotation.x = Math.sin(t * 8 + Math.PI) * 0.25;
      }
      if (headRef.current) {
        headRef.current.rotation.y = Math.sin(t * 2) * 0.08;
        headRef.current.rotation.x = Math.sin(t * 3) * 0.04 - 0.05;
      }
    } else if (isBlocked) {
      // Subtle frustrated fidget
      if (headRef.current) {
        headRef.current.rotation.z = Math.sin(t * 4) * 0.05;
      }
    } else if (isWaiting) {
      // Looking around
      if (headRef.current) {
        headRef.current.rotation.y = Math.sin(t * 1.5) * 0.25;
      }
    } else {
      // Idle: gentle breathing bob
      if (groupRef.current) {
        groupRef.current.position.y = position[1] + Math.sin(t * 1.2) * 0.02;
      }
      if (headRef.current) {
        headRef.current.rotation.y = Math.sin(t * 0.8) * 0.06;
      }
    }

    // Walking leg animation (idle sway for non-idle states)
    if (isBusy) {
      if (rightLegRef.current) rightLegRef.current.rotation.x = 0;
      if (leftLegRef.current) leftLegRef.current.rotation.x = 0;
    }
  });

  const statusColor = getStatusColor(status);

  return (
    <group
      ref={groupRef}
      position={position}
      onClick={(e) => { e.stopPropagation(); onClick(); }}
    >
      {/* Selection ring on floor */}
      {isSelected && (
        <mesh position={[0, 0.02, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.55, 0.65, 32]} />
          <meshBasicMaterial color="#54E1C1" side={THREE.DoubleSide} transparent opacity={0.8} />
        </mesh>
      )}

      {/* Status indicator floating above head */}
      <mesh position={[0, 2.35, 0]}>
        <sphereGeometry args={[0.1, 8, 8]} />
        <meshBasicMaterial color={statusColor} />
      </mesh>

      {/* Blocked warning sign */}
      {isBlocked && (
        <mesh position={[0.35, 2.1, 0]}>
          <boxGeometry args={[0.15, 0.15, 0.02]} />
          <meshBasicMaterial color="#E74C3C" />
        </mesh>
      )}

      {/* Waiting approval badge */}
      {isWaiting && (
        <mesh position={[0.35, 2.1, 0]}>
          <boxGeometry args={[0.15, 0.15, 0.02]} />
          <meshBasicMaterial color="#F39C12" />
        </mesh>
      )}

      {/* ── HEAD ── */}
      <group ref={headRef} position={[0, 1.7, 0]}>
        {/* Main head cube */}
        <mesh castShadow>
          <boxGeometry args={[0.5, 0.5, 0.5]} />
          <meshStandardMaterial color={skin.skinTone} roughness={0.7} />
        </mesh>

        {/* Hair (top block) */}
        <mesh position={[0, 0.27, -0.02]} castShadow>
          <boxGeometry args={[0.52, 0.08, 0.54]} />
          <meshStandardMaterial color={skin.hairColor} roughness={0.8} />
        </mesh>
        {/* Hair sides */}
        <mesh position={[0, 0.12, -0.24]} castShadow>
          <boxGeometry args={[0.52, 0.3, 0.06]} />
          <meshStandardMaterial color={skin.hairColor} roughness={0.8} />
        </mesh>

        {/* Eyes - left */}
        <mesh position={[-0.1, 0.04, 0.251]}>
          <boxGeometry args={[0.08, 0.06, 0.01]} />
          <meshBasicMaterial color={skin.eyeColor} />
        </mesh>
        {/* Eye white - left */}
        <mesh position={[-0.1, 0.04, 0.252]}>
          <boxGeometry args={[0.1, 0.08, 0.005]} />
          <meshBasicMaterial color="#FFFFFF" />
        </mesh>
        {/* Pupil - left */}
        <mesh position={[-0.1, 0.04, 0.255]}>
          <boxGeometry args={[0.05, 0.05, 0.005]} />
          <meshBasicMaterial color={skin.eyeColor} />
        </mesh>

        {/* Eyes - right */}
        <mesh position={[0.1, 0.04, 0.252]}>
          <boxGeometry args={[0.1, 0.08, 0.005]} />
          <meshBasicMaterial color="#FFFFFF" />
        </mesh>
        <mesh position={[0.1, 0.04, 0.255]}>
          <boxGeometry args={[0.05, 0.05, 0.005]} />
          <meshBasicMaterial color={skin.eyeColor} />
        </mesh>

        {/* Mouth */}
        <mesh position={[0, -0.1, 0.251]}>
          <boxGeometry args={[0.14, 0.04, 0.01]} />
          <meshBasicMaterial color="#B8706B" />
        </mesh>

        {/* Glasses (if applicable) */}
        {skin.hasGlasses && (
          <>
            <mesh position={[-0.1, 0.04, 0.26]}>
              <ringGeometry args={[0.055, 0.07, 4]} />
              <meshBasicMaterial color="#333333" side={THREE.DoubleSide} />
            </mesh>
            <mesh position={[0.1, 0.04, 0.26]}>
              <ringGeometry args={[0.055, 0.07, 4]} />
              <meshBasicMaterial color="#333333" side={THREE.DoubleSide} />
            </mesh>
            <mesh position={[0, 0.06, 0.26]}>
              <boxGeometry args={[0.04, 0.015, 0.005]} />
              <meshBasicMaterial color="#333333" />
            </mesh>
          </>
        )}

        {/* Headset (manager) */}
        {skin.hasHeadset && (
          <>
            <mesh position={[0, 0.22, 0]}>
              <torusGeometry args={[0.28, 0.02, 8, 16, Math.PI]} />
              <meshStandardMaterial color="#333333" />
            </mesh>
            <mesh position={[-0.28, 0.02, 0.1]}>
              <sphereGeometry args={[0.05, 6, 6]} />
              <meshStandardMaterial color="#333333" />
            </mesh>
          </>
        )}

        {/* Hat (devops) */}
        {skin.hasHat && (
          <>
            <mesh position={[0, 0.32, 0.02]} castShadow>
              <boxGeometry args={[0.55, 0.1, 0.55]} />
              <meshStandardMaterial color={skin.hatColor || '#2C3E50'} roughness={0.6} />
            </mesh>
            <mesh position={[0, 0.38, 0.02]} castShadow>
              <boxGeometry args={[0.4, 0.12, 0.4]} />
              <meshStandardMaterial color={skin.hatColor || '#2C3E50'} roughness={0.6} />
            </mesh>
          </>
        )}
      </group>

      {/* ── TORSO ── */}
      <mesh position={[0, 1.15, 0]} castShadow>
        <boxGeometry args={[0.5, 0.6, 0.3]} />
        <meshStandardMaterial color={skin.shirtColor} roughness={0.6} />
      </mesh>

      {/* Shirt detail/collar */}
      <mesh position={[0, 1.38, 0.14]}>
        <boxGeometry args={[0.2, 0.08, 0.04]} />
        <meshStandardMaterial color={skin.skinTone} roughness={0.7} />
      </mesh>

      {/* Accessory on chest (tie/badge) */}
      <mesh position={[0, 1.18, 0.16]}>
        <boxGeometry args={[0.06, 0.2, 0.02]} />
        <meshStandardMaterial color={skin.accessoryColor} roughness={0.4} metalness={0.3} />
      </mesh>

      {/* ── RIGHT ARM ── */}
      <group ref={rightArmRef} position={[0.35, 1.35, 0]}>
        <mesh position={[0, -0.22, 0]} castShadow>
          <boxGeometry args={[0.18, 0.5, 0.22]} />
          <meshStandardMaterial color={skin.shirtColor} roughness={0.6} />
        </mesh>
        {/* Hand */}
        <mesh position={[0, -0.5, 0]} castShadow>
          <boxGeometry args={[0.14, 0.1, 0.18]} />
          <meshStandardMaterial color={skin.skinTone} roughness={0.7} />
        </mesh>
      </group>

      {/* ── LEFT ARM ── */}
      <group ref={leftArmRef} position={[-0.35, 1.35, 0]}>
        <mesh position={[0, -0.22, 0]} castShadow>
          <boxGeometry args={[0.18, 0.5, 0.22]} />
          <meshStandardMaterial color={skin.shirtColor} roughness={0.6} />
        </mesh>
        <mesh position={[0, -0.5, 0]} castShadow>
          <boxGeometry args={[0.14, 0.1, 0.18]} />
          <meshStandardMaterial color={skin.skinTone} roughness={0.7} />
        </mesh>
      </group>

      {/* ── RIGHT LEG ── */}
      <group ref={rightLegRef} position={[0.12, 0.55, 0]}>
        <mesh position={[0, -0.2, 0]} castShadow>
          <boxGeometry args={[0.2, 0.5, 0.22]} />
          <meshStandardMaterial color={skin.pantsColor} roughness={0.7} />
        </mesh>
        <mesh position={[0, -0.48, 0.03]} castShadow>
          <boxGeometry args={[0.2, 0.08, 0.28]} />
          <meshStandardMaterial color={skin.shoeColor} roughness={0.5} />
        </mesh>
      </group>

      {/* ── LEFT LEG ── */}
      <group ref={leftLegRef} position={[-0.12, 0.55, 0]}>
        <mesh position={[0, -0.2, 0]} castShadow>
          <boxGeometry args={[0.2, 0.5, 0.22]} />
          <meshStandardMaterial color={skin.pantsColor} roughness={0.7} />
        </mesh>
        <mesh position={[0, -0.48, 0.03]} castShadow>
          <boxGeometry args={[0.2, 0.08, 0.28]} />
          <meshStandardMaterial color={skin.shoeColor} roughness={0.5} />
        </mesh>
      </group>
    </group>
  );
}

/* ═══════════════ DESK WITH MONITOR ═══════════════ */
function OfficeDeskUnit({ position, rotation = 0, accentColor }: {
  position: [number, number, number];
  rotation?: number;
  accentColor: string;
}) {
  return (
    <group position={position} rotation={[0, rotation, 0]}>
      {/* Desk top */}
      <mesh position={[0, 0.72, -0.4]} castShadow receiveShadow>
        <boxGeometry args={[1.6, 0.06, 0.8]} />
        <meshStandardMaterial color={PALETTE.deskTop} roughness={0.5} />
      </mesh>

      {/* Desk front panel */}
      <mesh position={[0, 0.36, -0.04]} castShadow>
        <boxGeometry args={[1.6, 0.7, 0.06]} />
        <meshStandardMaterial color={PALETTE.desk} roughness={0.6} />
      </mesh>

      {/* Desk legs */}
      {[[-0.7, 0.36, -0.7], [0.7, 0.36, -0.7]].map((pos, i) => (
        <mesh key={i} position={pos as [number, number, number]} castShadow>
          <boxGeometry args={[0.06, 0.7, 0.06]} />
          <meshStandardMaterial color={PALETTE.desk} roughness={0.6} />
        </mesh>
      ))}

      {/* Monitor */}
      <mesh position={[0, 1.15, -0.55]} castShadow>
        <boxGeometry args={[0.8, 0.5, 0.04]} />
        <meshStandardMaterial color={PALETTE.monitor} roughness={0.3} metalness={0.2} />
      </mesh>

      {/* Monitor screen */}
      <mesh position={[0, 1.15, -0.528]}>
        <planeGeometry args={[0.72, 0.42]} />
        <meshBasicMaterial color={accentColor} transparent opacity={0.7} />
      </mesh>

      {/* Monitor stand */}
      <mesh position={[0, 0.85, -0.55]} castShadow>
        <boxGeometry args={[0.08, 0.2, 0.08]} />
        <meshStandardMaterial color={PALETTE.monitor} roughness={0.3} />
      </mesh>
      <mesh position={[0, 0.76, -0.55]} castShadow>
        <boxGeometry args={[0.25, 0.03, 0.15]} />
        <meshStandardMaterial color={PALETTE.monitor} roughness={0.3} />
      </mesh>

      {/* Keyboard */}
      <mesh position={[0, 0.76, -0.3]}>
        <boxGeometry args={[0.4, 0.02, 0.15]} />
        <meshStandardMaterial color="#3D3D3D" roughness={0.4} />
      </mesh>

      {/* Mouse */}
      <mesh position={[0.35, 0.76, -0.3]}>
        <boxGeometry args={[0.08, 0.02, 0.12]} />
        <meshStandardMaterial color="#3D3D3D" roughness={0.4} />
      </mesh>

      {/* Chair */}
      <mesh position={[0, 0.38, 0.3]} castShadow>
        <boxGeometry args={[0.45, 0.06, 0.45]} />
        <meshStandardMaterial color={PALETTE.chair} roughness={0.5} />
      </mesh>
      {/* Chair back */}
      <mesh position={[0, 0.65, 0.5]} castShadow>
        <boxGeometry args={[0.45, 0.5, 0.06]} />
        <meshStandardMaterial color={PALETTE.chair} roughness={0.5} />
      </mesh>
      {/* Chair pedestal */}
      <mesh position={[0, 0.2, 0.3]} castShadow>
        <cylinderGeometry args={[0.04, 0.04, 0.35, 8]} />
        <meshStandardMaterial color="#666666" roughness={0.3} metalness={0.5} />
      </mesh>
      {/* Chair base */}
      <mesh position={[0, 0.04, 0.3]}>
        <cylinderGeometry args={[0.2, 0.2, 0.04, 8]} />
        <meshStandardMaterial color="#555555" roughness={0.4} metalness={0.4} />
      </mesh>

      {/* Desk accent LED strip */}
      <mesh position={[0, 0.74, -0.03]}>
        <boxGeometry args={[1.5, 0.015, 0.015]} />
        <meshBasicMaterial color={accentColor} />
      </mesh>
    </group>
  );
}

/* ═══════════════ OFFICE DECORATIONS ═══════════════ */
function PottedPlant({ position }: { position: [number, number, number] }) {
  return (
    <group position={position}>
      {/* Pot */}
      <mesh position={[0, 0.15, 0]} castShadow>
        <cylinderGeometry args={[0.12, 0.15, 0.3, 8]} />
        <meshStandardMaterial color={PALETTE.pot} roughness={0.7} />
      </mesh>
      {/* Foliage blocks (voxel-style leaves) */}
      {[
        [0, 0.45, 0], [-0.08, 0.55, 0.05], [0.08, 0.55, -0.05],
        [0, 0.6, 0], [-0.05, 0.5, -0.08], [0.06, 0.48, 0.06],
      ].map((pos, i) => (
        <mesh key={i} position={pos as [number, number, number]} castShadow>
          <boxGeometry args={[0.1, 0.1, 0.1]} />
          <meshStandardMaterial
            color={i % 2 === 0 ? PALETTE.plant : '#4A7A49'}
            roughness={0.8}
          />
        </mesh>
      ))}
    </group>
  );
}

function Bookshelf({ position, rotation = 0 }: { position: [number, number, number]; rotation?: number }) {
  return (
    <group position={position} rotation={[0, rotation, 0]}>
      {/* Frame */}
      <mesh position={[0, 0.75, 0]} castShadow>
        <boxGeometry args={[1.0, 1.5, 0.25]} />
        <meshStandardMaterial color={PALETTE.bookshelf} roughness={0.7} />
      </mesh>
      {/* Shelves */}
      {[0.3, 0.7, 1.1].map((y, i) => (
        <mesh key={i} position={[0, y, 0.02]}>
          <boxGeometry args={[0.9, 0.04, 0.22]} />
          <meshStandardMaterial color="#8B6F47" roughness={0.6} />
        </mesh>
      ))}
      {/* Books (colored blocks) */}
      {[
        { pos: [-0.3, 0.48, 0.03], color: '#C0392B', size: [0.08, 0.25, 0.15] },
        { pos: [-0.15, 0.46, 0.03], color: '#2980B9', size: [0.08, 0.2, 0.15] },
        { pos: [0, 0.48, 0.03], color: '#27AE60', size: [0.08, 0.25, 0.15] },
        { pos: [0.15, 0.45, 0.03], color: '#F39C12', size: [0.08, 0.18, 0.15] },
        { pos: [0.3, 0.47, 0.03], color: '#8E44AD', size: [0.08, 0.22, 0.15] },
        { pos: [-0.2, 0.88, 0.03], color: '#16A085', size: [0.08, 0.22, 0.15] },
        { pos: [0.1, 0.86, 0.03], color: '#D35400', size: [0.08, 0.18, 0.15] },
        { pos: [0.25, 0.88, 0.03], color: '#2C3E50', size: [0.08, 0.22, 0.15] },
      ].map((book, i) => (
        <mesh key={i} position={book.pos as [number, number, number]}>
          <boxGeometry args={book.size as [number, number, number]} />
          <meshStandardMaterial color={book.color} roughness={0.6} />
        </mesh>
      ))}
    </group>
  );
}

function DeskLamp({ position }: { position: [number, number, number] }) {
  return (
    <group position={position}>
      <mesh position={[0, 0, 0]}>
        <cylinderGeometry args={[0.06, 0.08, 0.03, 8]} />
        <meshStandardMaterial color="#333333" roughness={0.4} metalness={0.3} />
      </mesh>
      <mesh position={[0, 0.18, 0]}>
        <cylinderGeometry args={[0.015, 0.015, 0.35, 6]} />
        <meshStandardMaterial color="#666666" roughness={0.3} metalness={0.5} />
      </mesh>
      <mesh position={[0.05, 0.35, 0]}>
        <coneGeometry args={[0.1, 0.1, 8]} />
        <meshStandardMaterial color={PALETTE.lamp} roughness={0.4} emissive={PALETTE.lamp} emissiveIntensity={0.3} />
      </mesh>
      <pointLight position={[0.05, 0.3, 0]} intensity={0.4} color="#FFF8E1" distance={2} />
    </group>
  );
}

function WallWithWindows() {
  return (
    <group>
      {/* Back wall */}
      <mesh position={[0, 1.5, -6]} receiveShadow>
        <boxGeometry args={[14, 3.5, 0.15]} />
        <meshStandardMaterial color={PALETTE.wall} roughness={0.8} />
      </mesh>

      {/* Windows (3 large) */}
      {[-3.5, 0, 3.5].map((x, i) => (
        <group key={i} position={[x, 1.8, -5.92]}>
          {/* Window glass */}
          <mesh>
            <planeGeometry args={[1.8, 1.6]} />
            <meshBasicMaterial color={PALETTE.window} transparent opacity={0.4} side={THREE.DoubleSide} />
          </mesh>
          {/* Window frame */}
          <mesh position={[0, 0, 0.01]}>
            <boxGeometry args={[1.9, 0.05, 0.03]} />
            <meshStandardMaterial color={PALETTE.windowFrame} />
          </mesh>
          <mesh position={[0, 0.8, 0.01]}>
            <boxGeometry args={[1.9, 0.05, 0.03]} />
            <meshStandardMaterial color={PALETTE.windowFrame} />
          </mesh>
          <mesh position={[0, -0.8, 0.01]}>
            <boxGeometry args={[1.9, 0.05, 0.03]} />
            <meshStandardMaterial color={PALETTE.windowFrame} />
          </mesh>
          {/* Vertical divider */}
          <mesh position={[0, 0, 0.01]}>
            <boxGeometry args={[0.05, 1.65, 0.03]} />
            <meshStandardMaterial color={PALETTE.windowFrame} />
          </mesh>
        </group>
      ))}

      {/* Left wall */}
      <mesh position={[-6.5, 1.5, -0.5]} receiveShadow>
        <boxGeometry args={[0.15, 3.5, 12]} />
        <meshStandardMaterial color={PALETTE.wallAccent} roughness={0.8} />
      </mesh>

      {/* Right wall */}
      <mesh position={[6.5, 1.5, -0.5]} receiveShadow>
        <boxGeometry args={[0.15, 3.5, 12]} />
        <meshStandardMaterial color={PALETTE.wallAccent} roughness={0.8} />
      </mesh>
    </group>
  );
}

/* ═══════════════ OFFICE FLOOR ═══════════════ */
function OfficeFloor() {
  const tiles: React.JSX.Element[] = [];
  const gridSize = 7;

  for (let x = -gridSize; x <= gridSize; x++) {
    for (let z = -gridSize; z <= gridSize; z++) {
      const isAlt = (x + z) % 2 === 0;
      tiles.push(
        <mesh
          key={`${x}-${z}`}
          position={[x * 0.95, -0.02, z * 0.95]}
          receiveShadow
        >
          <boxGeometry args={[0.93, 0.04, 0.93]} />
          <meshStandardMaterial
            color={isAlt ? PALETTE.floor : PALETTE.floorTile}
            roughness={0.8}
          />
        </mesh>
      );
    }
  }

  return (
    <group>
      {tiles}

      {/* Central carpet/rug under builder desk */}
      <mesh position={[0, -0.005, 1]} receiveShadow>
        <boxGeometry args={[3, 0.02, 2.5]} />
        <meshStandardMaterial color={PALETTE.carpet} roughness={0.9} />
      </mesh>
    </group>
  );
}

function ManagerCatCharacter({
  status,
  isSelected,
  onClick,
  position = [0, 0, 0.6],
}: {
  status: string;
  isSelected: boolean;
  onClick: () => void;
  position?: [number, number, number];
}) {
  const gltf = useGLTF('/models/ai-manager-cat.glb');
  const clonedScene = React.useMemo(() => skeletonClone(gltf.scene), [gltf.scene]);
  const mixerRef = React.useRef<THREE.AnimationMixer | null>(null);

  React.useEffect(() => {
    if (!clonedScene) return;
    const mixer = new THREE.AnimationMixer(clonedScene);
    mixerRef.current = mixer;

    const clipName = status === 'busy' || status === 'working' ? 'speaking' : 'idle';
    const clip = gltf.animations.find((c) => c.name === clipName) || gltf.animations[0];
    if (clip) {
      mixer.clipAction(clip).play();
    }
    return () => {
      mixer.stopAllAction();
    };
  }, [clonedScene, gltf.animations, status]);

  useFrame((_, delta) => {
    mixerRef.current?.update(Math.min(delta, 0.1));
  });

  return (
    <group
      position={position}
      scale={[0.75, 0.75, 0.75]}
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
    >
      <primitive object={clonedScene} position={[0, 0.68, 0]} />
      {/* Selection ring */}
      {isSelected && (
        <mesh position={[0, 0.02, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.55, 0.65, 32]} />
          <meshBasicMaterial color="#54E1C1" />
        </mesh>
      )}
    </group>
  );
}

/* ═══════════════ WORKSTATION ASSEMBLY ═══════════════ */
function WorkstationUnit({
  config,
  employee,
  isSelected,
  onSelect,
}: {
  config: StationConfig;
  employee?: OfficeEmployeeState;
  _workstation?: WorkstationState;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const skin = CHARACTER_SKINS[config.role];
  const status = employee?.status || 'idle';
  const statusColor = getStatusColor(status);

  return (
    <group position={config.position} rotation={[0, config.rotation || 0, 0]}>
      {/* Desk */}
      <OfficeDeskUnit
        position={[0, 0, 0]}
        accentColor={statusColor}
      />

      {/* Floor zone indicator */}
      <mesh position={[0, 0.005, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[2.2, 2.2]} />
        <meshStandardMaterial
          color={isSelected ? '#2C5F5A' : PALETTE.floor}
          roughness={0.9}
          transparent
          opacity={isSelected ? 0.3 : 0}
        />
      </mesh>

      {/* Name label */}
      <Text
        position={[0, 2.6, 0]}
        fontSize={0.2}
        color={isSelected ? '#54E1C1' : '#2C3E50'}
        anchorX="center"
        anchorY="middle"
        outlineWidth={0.015}
        outlineColor="#FFFFFF"
      >
        {config.name}
      </Text>

      {/* Status label */}
      <Text
        position={[0, 2.35, 0]}
        fontSize={0.14}
        color={statusColor}
        anchorX="center"
        anchorY="middle"
      >
        {getStatusLabel(status)}
      </Text>

      {/* Character */}
      {config.role === 'manager' ? (
        <ManagerCatCharacter
          status={status}
          isSelected={isSelected}
          onClick={onSelect}
          position={[0, 0, 0.6]}
        />
      ) : (
        <MinecraftCharacter
          skin={skin}
          status={status}
          isSelected={isSelected}
          onClick={onSelect}
          position={[0, 0, 0.6]}
        />
      )}
    </group>
  );
}

/* ═══════════════ SCENE LIGHTING ═══════════════ */
function OfficeLighting() {
  return (
    <>
      {/* Warm ambient */}
      <ambientLight intensity={0.55} color="#FFF5E6" />

      {/* Main directional (sun through windows) */}
      <directionalLight
        position={[6, 12, -4]}
        intensity={1.0}
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-camera-left={-10}
        shadow-camera-right={10}
        shadow-camera-top={10}
        shadow-camera-bottom={-10}
        color="#FFF8E1"
      />

      {/* Fill light from front */}
      <directionalLight
        position={[-4, 8, 8]}
        intensity={0.4}
        color="#E8F4FF"
      />

      {/* Accent ceiling point light */}
      <pointLight position={[0, 4, 0]} intensity={0.6} color="#FFF5E6" distance={12} />

      {/* Window glow */}
      <pointLight position={[0, 2.5, -5.5]} intensity={0.3} color="#87CEEB" distance={8} />
    </>
  );
}

/* ═══════════════ MAIN CANVAS EXPORT ═══════════════ */
export interface ThreeOfficeCanvasProps {
  employees: OfficeEmployeeState[];
  workstations: WorkstationState[];
  selectedRole: AgentRole | null;
  onSelectRole: (role: AgentRole) => void;
}

function CameraPresetHandler({
  preset,
  onResetPreset,
}: {
  preset: string | null;
  onResetPreset: () => void;
}) {
  const { camera } = useThree();
  useFrame((_, delta) => {
    if (!preset) return;
    const targetPos =
      preset === 'iso'
        ? new THREE.Vector3(9, 7.5, 9)
        : preset === 'top'
          ? new THREE.Vector3(0, 14, 0.1)
          : new THREE.Vector3(0, 4, 11);

    const step = Math.min(delta * 5, 0.25);
    camera.position.lerp(targetPos, step);
    if (camera.position.distanceTo(targetPos) < 0.15) {
      onResetPreset();
    }
  });
  return null;
}

export default function ThreeOfficeCanvas({
  employees,
  workstations,
  selectedRole,
  onSelectRole,
}: ThreeOfficeCanvasProps) {
  const [cameraPreset, setCameraPreset] = React.useState<string | null>(null);

  const employeeMap = React.useMemo(() => {
    const map = new Map<AgentRole, OfficeEmployeeState>();
    employees.forEach((e) => map.set(e.role, e));
    return map;
  }, [employees]);

  const workstationMap = React.useMemo(() => {
    const map = new Map<string, WorkstationState>();
    workstations.forEach((w) => map.set(w.id, w));
    return map;
  }, [workstations]);

  return (
    <div className="relative w-full h-[600px] rounded-xl overflow-hidden border border-border bg-[#0E131D] select-none shadow-sm">
      <Canvas
        camera={{ position: [9, 7.5, 9], fov: 36 }}
        shadows
        dpr={[1, 1.5]}
        gl={{
          antialias: true,
          alpha: false,
          powerPreference: 'high-performance',
          stencil: false,
        }}
        onCreated={({ gl }) => {
          gl.setClearColor('#0E131D');
          gl.shadowMap.type = THREE.PCFSoftShadowMap;
        }}
      >
        <OfficeLighting />
        <CameraPresetHandler
          preset={cameraPreset}
          onResetPreset={() => setCameraPreset(null)}
        />

        <OrbitControls
          enablePan
          enableZoom
          enableRotate
          target={[0, 0.7, 0]}
          minPolarAngle={Math.PI / 6}
          maxPolarAngle={Math.PI / 2.2}
          minDistance={6}
          maxDistance={20}
          dampingFactor={0.08}
          enableDamping
        />

        {/* Floor */}
        <OfficeFloor />

        {/* Walls */}
        <WallWithWindows />

        {/* Decorations */}
        <PottedPlant position={[-5.5, 0, -4.5]} />
        <PottedPlant position={[5.5, 0, -4.5]} />
        <PottedPlant position={[-5.5, 0, 4]} />
        <PottedPlant position={[5.5, 0, 4]} />
        <PottedPlant position={[0, 0, -5]} />

        <Bookshelf position={[-6, 0, 0]} rotation={Math.PI / 2} />
        <Bookshelf position={[-6, 0, 2.5]} rotation={Math.PI / 2} />
        <Bookshelf position={[6, 0, 0]} rotation={-Math.PI / 2} />

        <DeskLamp position={[-0.6, 0.75, -3.7]} />
        <DeskLamp position={[0.6, 0.75, 0.7]} />

        {/* Workstations with characters */}
        {STATIONS.map((station) => (
          <WorkstationUnit
            key={station.role}
            config={station}
            employee={employeeMap.get(station.role)}
            _workstation={workstationMap.get(
              station.role === 'manager'
                ? 'manager_desk'
                : station.role === 'pm'
                  ? 'planning_desk'
                  : station.role === 'designer'
                    ? 'design_station'
                    : station.role === 'builder'
                      ? 'development_station'
                      : station.role === 'qa'
                        ? 'qa_station'
                        : station.role === 'reviewer'
                          ? 'review_area'
                          : 'operations_station'
            )}
            isSelected={selectedRole === station.role}
            onSelect={() => onSelectRole(station.role)}
          />
        ))}
      </Canvas>

      {/* Camera Presets Toolbar (Top Left) */}
      <div className="absolute top-3 left-3 z-10 flex items-center gap-1.5 p-1 rounded-lg bg-surface/90 border border-border backdrop-blur-md shadow-xs">
        <button
          type="button"
          onClick={() => setCameraPreset('iso')}
          className="px-2 py-1 rounded text-[11px] font-medium text-foreground hover:bg-surface-raised transition-colors"
          title="Isometric View"
        >
          Isometric
        </button>
        <button
          type="button"
          onClick={() => setCameraPreset('top')}
          className="px-2 py-1 rounded text-[11px] font-medium text-foreground hover:bg-surface-raised transition-colors"
          title="Top-down Floorplan"
        >
          Top-down
        </button>
        <button
          type="button"
          onClick={() => setCameraPreset('front')}
          className="px-2 py-1 rounded text-[11px] font-medium text-foreground hover:bg-surface-raised transition-colors"
          title="Front View"
        >
          Front
        </button>
        <button
          type="button"
          onClick={() => setCameraPreset('iso')}
          className="inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium text-accent hover:bg-surface-raised transition-colors border-l border-border pl-2 ml-0.5"
          title="Reset Camera (Isometric Snap)"
        >
          <RotateCcw className="h-3 w-3" />
          <span>Reset</span>
        </button>
      </div>

      {/* Status & Hints (Bottom Overlay) */}
      <div className="absolute bottom-3 left-3 pointer-events-none text-[11px] font-sans text-muted-foreground bg-surface/90 px-3 py-1.5 rounded-lg border border-border backdrop-blur-md flex items-center gap-2.5 shadow-xs">
        <span className="h-2 w-2 rounded-full bg-success animate-pulse" />
        <span className="font-medium text-foreground">3D Virtual Office</span>
        <span className="text-border">•</span>
        <span>Click agent to inspect • Drag to rotate • Scroll to zoom</span>
      </div>

      {/* Active Team Counter (Top Right) */}
      <div className="absolute top-3 right-3 pointer-events-none text-[10px] font-mono text-muted-foreground bg-surface/90 px-2.5 py-1 rounded-lg border border-border backdrop-blur-md">
        {employees.length} agents stationed
      </div>
    </div>
  );
}
