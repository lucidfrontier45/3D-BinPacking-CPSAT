declare module 'three' {
  export type ColorRepresentation = string | number | Color

  export class Color {
    constructor(color: ColorRepresentation)
    set(color: ColorRepresentation): this
  }

  export class Vector2 {
    x: number
    y: number
    constructor(x?: number, y?: number)
  }

  export class Vector3 {
    x: number
    y: number
    z: number
    constructor(x?: number, y?: number, z?: number)
    set(x: number, y: number, z: number): this
  }

  export class Object3D {
    position: Vector3
    userData: Record<string, unknown>
    add(...objects: Object3D[]): this
  }

  export class Scene extends Object3D {
    background: Color | null
    traverse(callback: (object: Object3D) => void): void
  }

  export class Camera extends Object3D {
    lookAt(target: Vector3): void
  }

  export class PerspectiveCamera extends Camera {
    aspect: number
    constructor(fov: number, aspect: number, near: number, far: number)
    updateProjectionMatrix(): void
  }

  export class Material {
    dispose(): void
  }

  export class MeshStandardMaterial extends Material {
    color: Color
    emissive: Color
    emissiveIntensity: number
    opacity: number
    transparent: boolean
    constructor(options?: {
      color?: ColorRepresentation
      roughness?: number
      metalness?: number
      transparent?: boolean
      opacity?: number
    })
  }

  export class LineBasicMaterial extends Material {
    constructor(options?: { color?: ColorRepresentation; transparent?: boolean; opacity?: number })
  }

  export class BufferGeometry {
    dispose(): void
  }

  export class BoxGeometry extends BufferGeometry {
    constructor(width?: number, height?: number, depth?: number)
  }

  export class EdgesGeometry extends BufferGeometry {
    constructor(geometry: BufferGeometry)
  }

  export class Mesh extends Object3D {
    geometry: BufferGeometry
    material: Material | Material[]
    constructor(geometry: BufferGeometry, material: Material | Material[])
  }

  export class LineSegments extends Object3D {
    geometry: BufferGeometry
    material: Material | Material[]
    constructor(geometry: BufferGeometry, material: Material | Material[])
  }

  export class HemisphereLight extends Object3D {
    constructor(skyColor: ColorRepresentation, groundColor: ColorRepresentation, intensity?: number)
  }

  export class DirectionalLight extends Object3D {
    constructor(color?: ColorRepresentation, intensity?: number)
  }

  export class GridHelper extends Object3D {
    constructor(size?: number, divisions?: number, color1?: ColorRepresentation, color2?: ColorRepresentation)
  }

  export type Intersection = { object: Object3D }

  export class Raycaster {
    setFromCamera(pointer: Vector2, camera: Camera): void
    intersectObjects(objects: Object3D[], recursive?: boolean): Intersection[]
  }

  export class WebGLRenderer {
    domElement: HTMLCanvasElement
    outputColorSpace: string
    toneMapping: number
    toneMappingExposure: number
    constructor(options?: { antialias?: boolean; alpha?: boolean })
    setPixelRatio(ratio: number): void
    setSize(width: number, height: number, updateStyle?: boolean): void
    render(scene: Scene, camera: Camera): void
    dispose(): void
  }

  export const SRGBColorSpace: string
  export const ACESFilmicToneMapping: number
}
