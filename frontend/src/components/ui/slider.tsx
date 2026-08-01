import * as React from "react"
import { Slider as SliderPrimitive } from "@base-ui/react/slider"

import { cn } from "@/lib/utils"

function Slider({ className, ...props }: React.ComponentProps<typeof SliderPrimitive>) {
  return (
    <SliderPrimitive
      data-slot="slider"
      className={cn(
        "h-2 w-full grow items-center rounded-sm bg-slider-track",
        className
      )}
      {...props}
    />
  )
}

export { Slider }