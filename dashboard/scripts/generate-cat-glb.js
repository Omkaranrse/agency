// Generator script: builds the official 3D Cat AI Manager GLB model
// using Three.js and GLTFExporter.

const fs = require('fs');
const path = require('path');

// Node.js polyfills for Three.js GLTFExporter
global.FileReader = class FileReader {
  readAsArrayBuffer(blob) {
    blob.arrayBuffer().then(buf => {
      this.result = buf;
      if (this.onloadend) this.onloadend({ target: this });
    });
  }
  readAsDataURL(blob) {
    blob.arrayBuffer().then(buf => {
      this.result = 'data:' + (blob.type || 'application/octet-stream') + ';base64,' + Buffer.from(buf).toString('base64');
      if (this.onloadend) this.onloadend({ target: this });
    });
  }
};

const THREE = require('three');
const { GLTFExporter } = require('three/examples/jsm/exporters/GLTFExporter.js');

function createCatModel() {
  const root = new THREE.Group();
  root.name = 'Root';

  // ── Materials ──
  // Gray fur for cat coat
  const furGrayMat = new THREE.MeshStandardMaterial({
    color: 0x767E8B,
    roughness: 0.65,
    metalness: 0.05,
    name: 'FurGray',
  });

  // White fur for muzzle, cheeks, chest underlay
  const furWhiteMat = new THREE.MeshStandardMaterial({
    color: 0xF4F6F8,
    roughness: 0.6,
    metalness: 0.02,
    name: 'FurWhite',
  });

  // Pink inner ears and nose
  const pinkMat = new THREE.MeshStandardMaterial({
    color: 0xF48FB1,
    roughness: 0.45,
    metalness: 0.0,
    name: 'EarNosePink',
  });

  // Emerald green eyes with subtle glow
  const eyeGreenMat = new THREE.MeshStandardMaterial({
    color: 0x10B981,
    emissive: 0x059669,
    emissiveIntensity: 0.35,
    roughness: 0.15,
    metalness: 0.1,
    name: 'EyeGreen',
  });

  // Black pupils & details
  const blackPupilMat = new THREE.MeshStandardMaterial({
    color: 0x0A0E17,
    roughness: 0.1,
    metalness: 0.2,
    name: 'PupilBlack',
  });

  // Eye specular catchlight
  const eyeHighlightMat = new THREE.MeshStandardMaterial({
    color: 0xFFFFFF,
    roughness: 0.05,
    metalness: 0.0,
    name: 'EyeHighlight',
  });

  // Suit Jacket & Pants: Deep Charcoal / Black tailored wool
  const suitFabricMat = new THREE.MeshStandardMaterial({
    color: 0x1A1F26,
    roughness: 0.8,
    metalness: 0.1,
    name: 'SuitBlack',
  });

  // Suit Lapels (slightly darker satin edge)
  const lapelMat = new THREE.MeshStandardMaterial({
    color: 0x12161B,
    roughness: 0.55,
    metalness: 0.2,
    name: 'SuitLapel',
  });

  // White Collared Shirt
  const shirtWhiteMat = new THREE.MeshStandardMaterial({
    color: 0xF8FAFC,
    roughness: 0.5,
    metalness: 0.05,
    name: 'ShirtWhite',
  });

  // Black Silk Tie
  const tieMat = new THREE.MeshStandardMaterial({
    color: 0x0F1318,
    roughness: 0.35,
    metalness: 0.3,
    name: 'TieBlack',
  });

  // Polished Executive Shoes
  const shoesMat = new THREE.MeshStandardMaterial({
    color: 0x0D1017,
    roughness: 0.25,
    metalness: 0.4,
    name: 'ShoesPolished',
  });

  // Whiskers (smooth white)
  const whiskerMat = new THREE.MeshStandardMaterial({
    color: 0xFFFFFF,
    roughness: 0.3,
    name: 'Whiskers',
  });

  // Dark Eyebrows
  const eyebrowMat = new THREE.MeshStandardMaterial({
    color: 0x2D3748,
    roughness: 0.7,
    name: 'Eyebrows',
  });

  // ── Hierarchy Setup ──
  const hips = new THREE.Group();
  hips.name = 'Hips';
  hips.position.set(0, 0.78, 0);
  root.add(hips);

  // Lower Torso / Pelvis suit jacket skirt
  const pelvisGeo = new THREE.CylinderGeometry(0.24, 0.26, 0.22, 24);
  pelvisGeo.scale(1.05, 1, 0.78);
  const pelvisMesh = new THREE.Mesh(pelvisGeo, suitFabricMat);
  pelvisMesh.position.y = -0.05;
  pelvisMesh.castShadow = true;
  hips.add(pelvisMesh);

  // ── Spine & Chest ──
  const spine = new THREE.Group();
  spine.name = 'Spine';
  spine.position.set(0, 0.08, 0);
  hips.add(spine);

  const chest = new THREE.Group();
  chest.name = 'Chest';
  chest.position.set(0, 0.22, 0);
  spine.add(chest);

  // Main Suit Torso
  const chestGeo = new THREE.CylinderGeometry(0.28, 0.24, 0.36, 24);
  chestGeo.scale(1.08, 1, 0.82);
  const chestMesh = new THREE.Mesh(chestGeo, suitFabricMat);
  chestMesh.castShadow = true;
  chestMesh.receiveShadow = true;
  chest.add(chestMesh);

  // White shirt V-front
  const shirtVGeo = new THREE.BufferGeometry();
  const shirtVVertices = new Float32Array([
    -0.12,  0.18, 0.19,
     0.12,  0.18, 0.19,
     0.0,  -0.08, 0.21,
  ]);
  shirtVGeo.setAttribute('position', new THREE.BufferAttribute(shirtVVertices, 3));
  shirtVGeo.computeVertexNormals();
  const shirtVMesh = new THREE.Mesh(shirtVGeo, shirtWhiteMat);
  chest.add(shirtVMesh);

  // Suit Left & Right Lapels
  const lapelGeo = new THREE.BoxGeometry(0.08, 0.32, 0.025);
  const leftLapel = new THREE.Mesh(lapelGeo, lapelMat);
  leftLapel.position.set(-0.11, 0.04, 0.20);
  leftLapel.rotation.set(0, 0, -0.22);
  leftLapel.castShadow = true;
  chest.add(leftLapel);

  const rightLapel = new THREE.Mesh(lapelGeo, lapelMat);
  rightLapel.position.set(0.11, 0.04, 0.20);
  rightLapel.rotation.set(0, 0, 0.22);
  rightLapel.castShadow = true;
  chest.add(rightLapel);

  // Black Tie Knot & Blade
  const tieKnotGeo = new THREE.ConeGeometry(0.038, 0.06, 4);
  tieKnotGeo.rotateZ(Math.PI);
  const tieKnot = new THREE.Mesh(tieKnotGeo, tieMat);
  tieKnot.position.set(0, 0.15, 0.215);
  chest.add(tieKnot);

  const tieBladeGeo = new THREE.BoxGeometry(0.046, 0.24, 0.015);
  const tieBlade = new THREE.Mesh(tieBladeGeo, tieMat);
  tieBlade.position.set(0, 0.02, 0.218);
  chest.add(tieBlade);

  // Left Breast Pocket & Folded Pocket Square
  const pocketGeo = new THREE.BoxGeometry(0.07, 0.012, 0.01);
  const pocketMesh = new THREE.Mesh(pocketGeo, lapelMat);
  pocketMesh.position.set(0.14, 0.08, 0.195);
  pocketMesh.rotation.set(0, 0, 0.06);
  chest.add(pocketMesh);

  const pocketSquareGeo = new THREE.BufferGeometry();
  const pocketSquareVerts = new Float32Array([
    0.115, 0.08, 0.20,
    0.165, 0.08, 0.20,
    0.14,  0.115, 0.202,
  ]);
  pocketSquareGeo.setAttribute('position', new THREE.BufferAttribute(pocketSquareVerts, 3));
  pocketSquareGeo.computeVertexNormals();
  const pocketSquareMesh = new THREE.Mesh(pocketSquareGeo, shirtWhiteMat);
  chest.add(pocketSquareMesh);

  // ── Neck & Head ──
  const neck = new THREE.Group();
  neck.name = 'Neck';
  neck.position.set(0, 0.22, 0);
  chest.add(neck);

  // White Shirt Collar around Neck
  const collarGeo = new THREE.CylinderGeometry(0.13, 0.14, 0.10, 20);
  const collarMesh = new THREE.Mesh(collarGeo, shirtWhiteMat);
  collarMesh.position.y = 0.02;
  neck.add(collarMesh);

  const head = new THREE.Group();
  head.name = 'Head';
  head.position.set(0, 0.18, 0.02);
  neck.add(head);

  // Cat Head Skull: Stylized, rounded executive cat skull
  const skullGeo = new THREE.SphereGeometry(0.36, 32, 28);
  skullGeo.scale(1.12, 0.96, 0.94);
  const skullMesh = new THREE.Mesh(skullGeo, furGrayMat);
  skullMesh.castShadow = true;
  skullMesh.receiveShadow = true;
  head.add(skullMesh);

  // Cat Cheeks (Left and Right fluffy white cheek pouches)
  const cheekGeo = new THREE.SphereGeometry(0.16, 20, 18);
  cheekGeo.scale(1.1, 0.9, 0.9);

  const leftCheek = new THREE.Mesh(cheekGeo, furWhiteMat);
  leftCheek.position.set(-0.16, -0.09, 0.22);
  leftCheek.castShadow = true;
  head.add(leftCheek);

  const rightCheek = new THREE.Mesh(cheekGeo, furWhiteMat);
  rightCheek.position.set(0.16, -0.09, 0.22);
  rightCheek.castShadow = true;
  head.add(rightCheek);

  // Central Muzzle / Chin pad
  const muzzleGeo = new THREE.SphereGeometry(0.14, 20, 16);
  muzzleGeo.scale(1.1, 0.75, 0.9);
  const muzzleMesh = new THREE.Mesh(muzzleGeo, furWhiteMat);
  muzzleMesh.position.set(0, -0.12, 0.24);
  muzzleMesh.castShadow = true;
  head.add(muzzleMesh);

  // Cute Triangular Pink Cat Nose
  const noseGeo = new THREE.ConeGeometry(0.042, 0.048, 3);
  noseGeo.rotateZ(Math.PI);
  noseGeo.scale(1.2, 1, 0.8);
  const noseMesh = new THREE.Mesh(noseGeo, pinkMat);
  noseMesh.position.set(0, -0.035, 0.35);
  head.add(noseMesh);

  // Whiskers (3 on each cheek, curved outward)
  const whiskerGeo = new THREE.CylinderGeometry(0.0025, 0.001, 0.24, 6);
  whiskerGeo.rotateZ(Math.PI / 2);

  const whiskerAngles = [-0.12, 0.0, 0.12];
  whiskerAngles.forEach((ang, i) => {
    // Left whiskers
    const wLeft = new THREE.Mesh(whiskerGeo, whiskerMat);
    wLeft.position.set(-0.25, -0.07 + ang * 0.4, 0.26);
    wLeft.rotation.set(0, 0.3, ang);
    head.add(wLeft);

    // Right whiskers
    const wRight = new THREE.Mesh(whiskerGeo, whiskerMat);
    wRight.position.set(0.25, -0.07 + ang * 0.4, 0.26);
    wRight.rotation.set(0, -0.3, -ang);
    head.add(wRight);
  });

  // Cat Ears (Left & Right with pink inner ear shell)
  function createEar(isLeft) {
    const earGroup = new THREE.Group();
    earGroup.name = isLeft ? 'LeftEar' : 'RightEar';

    // Outer gray ear cone
    const outerGeo = new THREE.ConeGeometry(0.14, 0.28, 4);
    outerGeo.scale(1, 1, 0.65);
    const outerMesh = new THREE.Mesh(outerGeo, furGrayMat);
    outerMesh.castShadow = true;
    earGroup.add(outerMesh);

    // Inner pink ear shell
    const innerGeo = new THREE.ConeGeometry(0.11, 0.23, 3);
    innerGeo.scale(0.9, 1, 0.4);
    const innerMesh = new THREE.Mesh(innerGeo, pinkMat);
    innerMesh.position.set(0, -0.015, 0.03);
    earGroup.add(innerMesh);

    const xSign = isLeft ? -1 : 1;
    earGroup.position.set(xSign * 0.22, 0.35, 0.02);
    earGroup.rotation.set(-0.1, 0, xSign * -0.32);
    return earGroup;
  }
  const leftEar = createEar(true);
  const rightEar = createEar(false);
  head.add(leftEar);
  head.add(rightEar);

  // Cat Eyes: Large, vivid emerald green eyes with deep pupils & specular catchlight
  function createEye(isLeft) {
    const eyeGroup = new THREE.Group();
    eyeGroup.name = isLeft ? 'LeftEye' : 'RightEye';

    // Sclera / Eye globe
    const globeGeo = new THREE.SphereGeometry(0.11, 24, 24);
    globeGeo.scale(1, 1, 0.65);
    const globe = new THREE.Mesh(globeGeo, furWhiteMat);
    eyeGroup.add(globe);

    // Iris (Vibrant Emerald Green)
    const irisGeo = new THREE.CircleGeometry(0.078, 24);
    const iris = new THREE.Mesh(irisGeo, eyeGreenMat);
    iris.position.set(0, 0, 0.072);
    eyeGroup.add(iris);

    // Pupil (Deep black circle)
    const pupilGeo = new THREE.CircleGeometry(0.046, 24);
    const pupil = new THREE.Mesh(pupilGeo, blackPupilMat);
    pupil.position.set(0, 0, 0.075);
    eyeGroup.add(pupil);

    // Specular catchlights (Crisp white highlights)
    const highlightGeo = new THREE.CircleGeometry(0.018, 16);
    const highlight = new THREE.Mesh(highlightGeo, eyeHighlightMat);
    highlight.position.set(-0.022, 0.024, 0.078);
    eyeGroup.add(highlight);

    const highlightGeo2 = new THREE.CircleGeometry(0.009, 12);
    const highlight2 = new THREE.Mesh(highlightGeo2, eyeHighlightMat);
    highlight2.position.set(0.016, -0.016, 0.078);
    eyeGroup.add(highlight2);

    // Eyelid for blinking animation
    const eyelidGeo = new THREE.SphereGeometry(0.115, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2);
    eyelidGeo.scale(1.02, 1.02, 0.68);
    const eyelid = new THREE.Mesh(eyelidGeo, furGrayMat);
    eyelid.name = isLeft ? 'LeftEyelid' : 'RightEyelid';
    eyelid.rotation.x = -Math.PI / 2; // Open by default
    eyelid.position.set(0, 0, 0.005);
    eyeGroup.add(eyelid);

    const xSign = isLeft ? -1 : 1;
    eyeGroup.position.set(xSign * 0.14, 0.06, 0.28);
    eyeGroup.rotation.set(0.05, xSign * -0.12, 0);
    return eyeGroup;
  }
  const leftEye = createEye(true);
  const rightEye = createEye(false);
  head.add(leftEye);
  head.add(rightEye);

  // Expressive Dark Eyebrows
  function createEyebrow(isLeft) {
    const browGeo = new THREE.BoxGeometry(0.11, 0.022, 0.025);
    const brow = new THREE.Mesh(browGeo, eyebrowMat);
    const xSign = isLeft ? -1 : 1;
    brow.name = isLeft ? 'LeftEyebrow' : 'RightEyebrow';
    brow.position.set(xSign * 0.14, 0.20, 0.29);
    brow.rotation.set(0.1, xSign * -0.15, xSign * -0.18);
    return brow;
  }
  const leftEyebrow = createEyebrow(true);
  const rightEyebrow = createEyebrow(false);
  head.add(leftEyebrow);
  head.add(rightEyebrow);

  // ── Arms & Hands (Suit sleeves with shirt cuffs & cat paws) ──
  function createArm(isLeft) {
    const shoulder = new THREE.Group();
    shoulder.name = isLeft ? 'LeftShoulder' : 'RightShoulder';
    const xSign = isLeft ? -1 : 1;
    shoulder.position.set(xSign * 0.28, 0.10, 0);
    chest.add(shoulder);

    // Shoulder cap
    const shoulderPadGeo = new THREE.SphereGeometry(0.09, 16, 14);
    const shoulderPad = new THREE.Mesh(shoulderPadGeo, suitFabricMat);
    shoulder.add(shoulderPad);

    const arm = new THREE.Group();
    arm.name = isLeft ? 'LeftArm' : 'RightArm';
    shoulder.add(arm);

    // Upper arm sleeve
    const upperArmGeo = new THREE.CylinderGeometry(0.075, 0.068, 0.22, 16);
    upperArmGeo.translate(0, -0.11, 0);
    const upperArmMesh = new THREE.Mesh(upperArmGeo, suitFabricMat);
    upperArmMesh.castShadow = true;
    arm.add(upperArmMesh);

    const forearm = new THREE.Group();
    forearm.name = isLeft ? 'LeftForearm' : 'RightForearm';
    forearm.position.set(0, -0.22, 0);
    arm.add(forearm);

    // Forearm sleeve
    const forearmGeo = new THREE.CylinderGeometry(0.068, 0.062, 0.20, 16);
    forearmGeo.translate(0, -0.10, 0);
    const forearmMesh = new THREE.Mesh(forearmGeo, suitFabricMat);
    forearmMesh.castShadow = true;
    forearm.add(forearmMesh);

    // White shirt cuff
    const cuffGeo = new THREE.CylinderGeometry(0.065, 0.065, 0.035, 16);
    cuffGeo.translate(0, -0.19, 0);
    const cuffMesh = new THREE.Mesh(cuffGeo, shirtWhiteMat);
    forearm.add(cuffMesh);

    const hand = new THREE.Group();
    hand.name = isLeft ? 'LeftHand' : 'RightHand';
    hand.position.set(0, -0.21, 0);
    forearm.add(hand);

    // Gray Cat Paw
    const pawGeo = new THREE.SphereGeometry(0.062, 16, 16);
    pawGeo.scale(1, 0.8, 1.2);
    const pawMesh = new THREE.Mesh(pawGeo, furGrayMat);
    pawMesh.castShadow = true;
    hand.add(pawMesh);

    return { shoulder, arm, forearm, hand };
  }
  createArm(true);
  createArm(false);

  // ── Legs & Executive Shoes ──
  function createLeg(isLeft) {
    const upLeg = new THREE.Group();
    upLeg.name = isLeft ? 'LeftUpLeg' : 'RightUpLeg';
    const xSign = isLeft ? -1 : 1;
    upLeg.position.set(xSign * 0.12, -0.14, 0);
    hips.add(upLeg);

    // Thigh trouser
    const thighGeo = new THREE.CylinderGeometry(0.088, 0.075, 0.28, 16);
    thighGeo.translate(0, -0.14, 0);
    const thighMesh = new THREE.Mesh(thighGeo, suitFabricMat);
    thighMesh.castShadow = true;
    upLeg.add(thighMesh);

    const leg = new THREE.Group();
    leg.name = isLeft ? 'LeftLeg' : 'RightLeg';
    leg.position.set(0, -0.28, 0);
    upLeg.add(leg);

    // Shin trouser
    const shinGeo = new THREE.CylinderGeometry(0.075, 0.068, 0.28, 16);
    shinGeo.translate(0, -0.14, 0);
    const shinMesh = new THREE.Mesh(shinGeo, suitFabricMat);
    shinMesh.castShadow = true;
    leg.add(shinMesh);

    const foot = new THREE.Group();
    foot.name = isLeft ? 'LeftFoot' : 'RightFoot';
    foot.position.set(0, -0.28, 0);
    leg.add(foot);

    // Polished executive dress shoes with rounded toe
    const shoeGeo = new THREE.BoxGeometry(0.11, 0.07, 0.20);
    shoeGeo.translate(0, 0.035, 0.04);
    const shoeMesh = new THREE.Mesh(shoeGeo, shoesMat);
    shoeMesh.castShadow = true;
    foot.add(shoeMesh);

    return { upLeg, leg, foot };
  }
  createLeg(true);
  createLeg(false);

  // ── Feline Tail (4 articulating segments curving upward) ──
  const tail1 = new THREE.Group();
  tail1.name = 'Tail1';
  tail1.position.set(0, -0.06, -0.18);
  tail1.rotation.x = -0.55;
  hips.add(tail1);

  const t1Geo = new THREE.CylinderGeometry(0.045, 0.05, 0.16, 12);
  t1Geo.translate(0, 0.08, 0);
  tail1.add(new THREE.Mesh(t1Geo, furGrayMat));

  const tail2 = new THREE.Group();
  tail2.name = 'Tail2';
  tail2.position.set(0, 0.16, 0);
  tail2.rotation.x = 0.35;
  tail1.add(tail2);

  const t2Geo = new THREE.CylinderGeometry(0.040, 0.045, 0.16, 12);
  t2Geo.translate(0, 0.08, 0);
  tail2.add(new THREE.Mesh(t2Geo, furGrayMat));

  const tail3 = new THREE.Group();
  tail3.name = 'Tail3';
  tail3.position.set(0, 0.16, 0);
  tail3.rotation.x = 0.45;
  tail2.add(tail3);

  const t3Geo = new THREE.CylinderGeometry(0.035, 0.040, 0.16, 12);
  t3Geo.translate(0, 0.08, 0);
  tail3.add(new THREE.Mesh(t3Geo, furGrayMat));

  const tail4 = new THREE.Group();
  tail4.name = 'Tail4';
  tail4.position.set(0, 0.16, 0);
  tail4.rotation.x = 0.35;
  tail3.add(tail4);

  // White tip at tail tip
  const t4Geo = new THREE.SphereGeometry(0.038, 12, 12);
  t4Geo.scale(1, 1.8, 1);
  t4Geo.translate(0, 0.08, 0);
  tail4.add(new THREE.Mesh(t4Geo, furWhiteMat));

  return root;
}

// ── Animation Helper ──
function makeQuatTrack(nodeName, times, quatEulerList) {
  const values = [];
  const euler = new THREE.Euler();
  const q = new THREE.Quaternion();

  for (const [x, y, z] of quatEulerList) {
    euler.set(x, y, z);
    q.setFromEuler(euler);
    values.push(q.x, q.y, q.z, q.w);
  }

  return new THREE.QuaternionKeyframeTrack(nodeName + '.quaternion', times, values);
}

function makePosTrack(nodeName, times, posList) {
  const values = [];
  for (const [x, y, z] of posList) {
    values.push(x, y, z);
  }
  return new THREE.VectorKeyframeTrack(nodeName + '.position', times, values);
}

function makeScaleTrack(nodeName, times, scaleList) {
  const values = [];
  for (const [x, y, z] of scaleList) {
    values.push(x, y, z);
  }
  return new THREE.VectorKeyframeTrack(nodeName + '.scale', times, values);
}

// ── Build Animation Clips ──
function createClips() {
  // 1. Idle Clip (4.0s smooth loop)
  const idleTracks = [
    // Chest breathing: subtle pitch & scale
    makeQuatTrack('Chest', [0, 1.0, 2.0, 3.0, 4.0], [
      [0, 0, 0],
      [0.025, 0, 0],
      [0, 0, 0],
      [0.025, 0, 0],
      [0, 0, 0],
    ]),
    makeScaleTrack('Chest', [0, 1.0, 2.0, 3.0, 4.0], [
      [1, 1, 1],
      [1.025, 1.015, 1.025],
      [1, 1, 1],
      [1.025, 1.015, 1.025],
      [1, 1, 1],
    ]),
    // Head: natural slight yaw & tilt
    makeQuatTrack('Head', [0, 1.0, 2.0, 3.0, 4.0], [
      [0, 0, 0],
      [-0.02, 0.03, 0.02],
      [0, 0, 0],
      [-0.015, -0.03, -0.02],
      [0, 0, 0],
    ]),
    // Tail waving gently
    makeQuatTrack('Tail1', [0, 1.0, 2.0, 3.0, 4.0], [
      [-0.55, 0, 0],
      [-0.50, 0.15, 0.05],
      [-0.55, 0, 0],
      [-0.50, -0.15, -0.05],
      [-0.55, 0, 0],
    ]),
    makeQuatTrack('Tail3', [0, 1.0, 2.0, 3.0, 4.0], [
      [0.45, 0, 0],
      [0.40, 0.25, 0.1],
      [0.45, 0, 0],
      [0.40, -0.25, -0.1],
      [0.45, 0, 0],
    ]),
    // Eye blinks (LeftEyelid and RightEyelid)
    makeQuatTrack('LeftEyelid', [0, 1.8, 1.9, 2.0, 4.0], [
      [-Math.PI / 2, 0, 0],
      [-Math.PI / 2, 0, 0],
      [0, 0, 0],
      [-Math.PI / 2, 0, 0],
      [-Math.PI / 2, 0, 0],
    ]),
    makeQuatTrack('RightEyelid', [0, 1.8, 1.9, 2.0, 4.0], [
      [-Math.PI / 2, 0, 0],
      [-Math.PI / 2, 0, 0],
      [0, 0, 0],
      [-Math.PI / 2, 0, 0],
      [-Math.PI / 2, 0, 0],
    ]),
    // Subtle arm sway
    makeQuatTrack('LeftArm', [0, 2.0, 4.0], [
      [0, 0, 0.08],
      [0.04, 0, 0.05],
      [0, 0, 0.08],
    ]),
    makeQuatTrack('RightArm', [0, 2.0, 4.0], [
      [0, 0, -0.08],
      [0.04, 0, -0.05],
      [0, 0, -0.08],
    ]),
  ];
  const idleClip = new THREE.AnimationClip('idle', 4.0, idleTracks);

  // 2. Listening Clip (2.5s loop): attentive lean, ears perked, hands attentive
  const listeningTracks = [
    makeQuatTrack('Head', [0, 1.25, 2.5], [
      [0.10, 0, 0],
      [0.14, 0.03, 0.02],
      [0.10, 0, 0],
    ]),
    makeQuatTrack('LeftEar', [0, 1.25, 2.5], [
      [-0.20, 0, -0.25],
      [-0.15, 0, -0.22],
      [-0.20, 0, -0.25],
    ]),
    makeQuatTrack('RightEar', [0, 1.25, 2.5], [
      [-0.20, 0, 0.25],
      [-0.15, 0, 0.22],
      [-0.20, 0, 0.25],
    ]),
    makeQuatTrack('RightArm', [0, 1.25, 2.5], [
      [-0.45, 0.2, -0.3],
      [-0.50, 0.22, -0.28],
      [-0.45, 0.2, -0.3],
    ]),
    makeQuatTrack('RightForearm', [0, 1.25, 2.5], [
      [-0.6, 0, 0],
      [-0.65, 0, 0],
      [-0.6, 0, 0],
    ]),
    makeQuatTrack('Tail1', [0, 1.25, 2.5], [
      [-0.6, 0.08, 0],
      [-0.55, -0.08, 0],
      [-0.6, 0.08, 0],
    ]),
  ];
  const listeningClip = new THREE.AnimationClip('listening', 2.5, listeningTracks);

  // 3. Thinking Clip (3.0s loop): head tilted, paw touching chin, thoughtful
  const thinkingTracks = [
    makeQuatTrack('Head', [0, 1.5, 3.0], [
      [-0.05, 0.18, 0.14],
      [-0.02, 0.22, 0.16],
      [-0.05, 0.18, 0.14],
    ]),
    makeQuatTrack('RightArm', [0, 1.5, 3.0], [
      [-0.95, 0.35, -0.45],
      [-1.00, 0.38, -0.42],
      [-0.95, 0.35, -0.45],
    ]),
    makeQuatTrack('RightForearm', [0, 1.5, 3.0], [
      [-1.35, -0.2, 0.4],
      [-1.40, -0.2, 0.4],
      [-1.35, -0.2, 0.4],
    ]),
    makeQuatTrack('LeftArm', [0, 1.5, 3.0], [
      [-0.35, -0.25, 0.35],
      [-0.38, -0.22, 0.32],
      [-0.35, -0.25, 0.35],
    ]),
    makeQuatTrack('LeftForearm', [0, 1.5, 3.0], [
      [-0.8, 0.2, 0],
      [-0.82, 0.2, 0],
      [-0.8, 0.2, 0],
    ]),
    makeQuatTrack('Tail4', [0, 0.8, 1.5, 2.3, 3.0], [
      [0.35, 0, 0],
      [0.35, 0.3, 0.1],
      [0.35, -0.1, 0],
      [0.35, 0.3, 0.1],
      [0.35, 0, 0],
    ]),
  ];
  const thinkingClip = new THREE.AnimationClip('thinking', 3.0, thinkingTracks);

  // 4. Speaking Clip (2.0s conversational loop): confident gestures, head nod
  const speakingTracks = [
    makeQuatTrack('Head', [0, 0.5, 1.0, 1.5, 2.0], [
      [0, 0, 0],
      [0.08, -0.05, -0.02],
      [-0.04, 0.06, 0.03],
      [0.06, 0.02, 0],
      [0, 0, 0],
    ]),
    makeQuatTrack('Chest', [0, 0.5, 1.0, 1.5, 2.0], [
      [0, 0, 0],
      [0.04, 0.02, 0],
      [-0.02, -0.02, 0],
      [0.03, 0.01, 0],
      [0, 0, 0],
    ]),
    makeQuatTrack('RightArm', [0, 0.5, 1.0, 1.5, 2.0], [
      [-0.4, 0.1, -0.2],
      [-0.7, 0.3, -0.4],
      [-0.45, 0.15, -0.25],
      [-0.65, 0.25, -0.35],
      [-0.4, 0.1, -0.2],
    ]),
    makeQuatTrack('RightForearm', [0, 0.5, 1.0, 1.5, 2.0], [
      [-0.5, 0, 0],
      [-0.85, 0, 0],
      [-0.55, 0, 0],
      [-0.75, 0, 0],
      [-0.5, 0, 0],
    ]),
    makeQuatTrack('LeftArm', [0, 0.5, 1.0, 1.5, 2.0], [
      [-0.5, -0.2, 0.3],
      [-0.35, -0.1, 0.15],
      [-0.65, -0.3, 0.4],
      [-0.4, -0.15, 0.2],
      [-0.5, -0.2, 0.3],
    ]),
    makeQuatTrack('LeftForearm', [0, 0.5, 1.0, 1.5, 2.0], [
      [-0.65, 0, 0],
      [-0.45, 0, 0],
      [-0.8, 0, 0],
      [-0.5, 0, 0],
      [-0.65, 0, 0],
    ]),
  ];
  const speakingClip = new THREE.AnimationClip('speaking', 2.0, speakingTracks);

  // 5. Success Clip (2.0s cheerful celebratory loop)
  const successTracks = [
    makePosTrack('Hips', [0, 0.5, 1.0, 1.5, 2.0], [
      [0, 0.78, 0],
      [0, 0.86, 0],
      [0, 0.78, 0],
      [0, 0.84, 0],
      [0, 0.78, 0],
    ]),
    makeQuatTrack('Head', [0, 0.5, 1.0, 1.5, 2.0], [
      [0, 0, 0],
      [-0.12, 0, 0],
      [0.04, 0, 0],
      [-0.10, 0, 0],
      [0, 0, 0],
    ]),
    makeQuatTrack('RightArm', [0, 0.5, 1.0, 1.5, 2.0], [
      [0, 0, -0.1],
      [-1.6, 0.4, -0.5],
      [-1.1, 0.2, -0.3],
      [-1.5, 0.35, -0.45],
      [0, 0, -0.1],
    ]),
    makeQuatTrack('LeftArm', [0, 0.5, 1.0, 1.5, 2.0], [
      [0, 0, 0.1],
      [-1.6, -0.4, 0.5],
      [-1.1, -0.2, 0.3],
      [-1.5, -0.35, 0.45],
      [0, 0, 0.1],
    ]),
    makeQuatTrack('Tail1', [0, 0.4, 0.8, 1.2, 1.6, 2.0], [
      [-0.5, 0, 0],
      [-0.4, 0.35, 0.2],
      [-0.4, -0.35, -0.2],
      [-0.4, 0.35, 0.2],
      [-0.4, -0.35, -0.2],
      [-0.5, 0, 0],
    ]),
  ];
  const successClip = new THREE.AnimationClip('success', 2.0, successTracks);

  // 6. Error Clip (2.5s sympathetic, calming posture)
  const errorTracks = [
    makeQuatTrack('Head', [0, 1.25, 2.5], [
      [0.12, 0.08, 0.06],
      [0.15, -0.06, -0.04],
      [0.12, 0.08, 0.06],
    ]),
    makeQuatTrack('RightArm', [0, 1.25, 2.5], [
      [-0.45, 0.3, -0.2],
      [-0.48, 0.32, -0.18],
      [-0.45, 0.3, -0.2],
    ]),
    makeQuatTrack('LeftArm', [0, 1.25, 2.5], [
      [-0.45, -0.3, 0.2],
      [-0.48, -0.32, 0.18],
      [-0.45, -0.3, 0.2],
    ]),
    makeQuatTrack('Tail1', [0, 1.25, 2.5], [
      [-0.65, 0.05, 0],
      [-0.65, -0.05, 0],
      [-0.65, 0.05, 0],
    ]),
  ];
  const errorClip = new THREE.AnimationClip('error', 2.5, errorTracks);

  return [idleClip, listeningClip, thinkingClip, speakingClip, successClip, errorClip];
}

// ── Main Execution ──
async function main() {
  const model = createCatModel();
  const clips = createClips();

  const scene = new THREE.Scene();
  scene.add(model);

  const exporter = new GLTFExporter();
  const outputPath = path.resolve(__dirname, '../public/models/ai-manager-cat.glb');

  console.log('Generating 3D Cat Mascot GLB...');
  const glbBuffer = await new Promise((resolve, reject) => {
    exporter.parse(
      scene,
      (result) => resolve(Buffer.from(result)),
      (err) => reject(err),
      {
        binary: true,
        animations: clips,
      }
    );
  });

  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, glbBuffer);
  console.log(`SUCCESS: Model generated at ${outputPath}`);
  console.log(`File size: ${(glbBuffer.length / 1024).toFixed(2)} KB`);
  console.log(`Embedded clips: ${clips.map(c => c.name).join(', ')}`);
}

main().catch(err => {
  console.error('Failed to generate 3D model:', err);
  process.exit(1);
});
