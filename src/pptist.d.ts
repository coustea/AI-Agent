declare module 'pptist' {
  import { DefineComponent } from 'vue'

  export const Screen: DefineComponent<{
    slides?: any[]
    slideIndex?: number
  }>

  export const Editor: DefineComponent<{
    slides?: any[]
  }>

  export type PPTSlide = {
    id: string
    elements: any[]
    background?: any
    turningMode?: string
    animations?: any[]
  }

  export type PPTElement = {
    id: string
    type: string
    left: number
    top: number
    width: number
    height: number
    rotate: number
    [key: string]: any
  }
}

declare module 'pptist/types/slides' {
  export interface Slide {
    id: string
    elements: any[]
    background?: any
    turningMode?: string
    animations?: any[]
  }

  export interface PPTElement {
    id: string
    type: string
    left: number
    top: number
    width: number
    height: number
    rotate: number
    [key: string]: any
  }

  export interface SlideBackground {
    type: string
    color?: string
    image?: any
    gradient?: any
  }
}