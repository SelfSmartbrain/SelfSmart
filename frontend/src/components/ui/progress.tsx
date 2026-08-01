import * as Progress from "@base-ui/react/progress";
import { cn } from "@/lib/utils";

const ProgressPrimitive = Progress.Root;

function Progress({ className, ...props }: any) {
  return (
    <ProgressPrimitive
      data-slot="progress"
      className={cn(
        "h-2 w-full grow rounded-full bg-primary/20",
        className
      )}
      {...props}
    />
  );
}

export { Progress };