import { MathUtils } from "three"

/** 카메라 극각(수직에서 기운 각도, rad). 이 아래에서는 공간 속 글자·패널을 지면에 눕힌다. */
export const FLAT_BELOW = MathUtils.degToRad(32)
/** 이 위에서는 공간 속 글자·패널을 지면 위에 세운다. */
export const UPRIGHT_ABOVE = MathUtils.degToRad(58)

/** 0 이면 눕힘, 1 이면 세움. 두 각도 사이는 부드럽게 잇는다. */
export const uprightAmount = (polar: number) => MathUtils.smoothstep(polar, FLAT_BELOW, UPRIGHT_ABOVE)
