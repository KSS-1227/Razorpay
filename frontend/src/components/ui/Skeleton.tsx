import type { HTMLAttributes } from 'react'

export function Skeleton({ className = '', ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded-xl bg-slate-800/60 shimmer-effect ${className}`}
      {...props}
    />
  )
}

export function FormSkeleton() {
  return (
    <div className="flex flex-col gap-5 w-full animate-fadeIn">
      <div className="flex flex-col gap-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-10 w-full" />
      </div>
      <div className="flex flex-col gap-2">
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-10 w-full" />
      </div>
      <Skeleton className="h-11 w-full mt-2" />
    </div>
  )
}
