"use client"

import { useRouter, useSearchParams } from "next/navigation"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

type QuerySelectProps = {
  name: string
  value?: string
  placeholder: string
  className?: string
  options: { value: string; label: string }[]
  /** URL query keys to drop when the value changes (typically pagination). */
  clearParamsOnChange?: string[]
}

export function QuerySelect({
  name,
  value = "all",
  placeholder,
  className,
  options,
  clearParamsOnChange = ["page"],
}: QuerySelectProps) {
  const router = useRouter()
  const searchParams = useSearchParams()

  const update = (nextValue: string) => {
    const params = new URLSearchParams(searchParams.toString())
    for (const key of clearParamsOnChange) {
      params.delete(key)
    }
    if (nextValue === "all") {
      params.delete(name)
    } else {
      params.set(name, nextValue)
    }
    router.push(`?${params.toString()}`)
  }

  return (
    <Select value={value} onValueChange={update}>
      <SelectTrigger className={className}>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {options.map((option) => (
          <SelectItem key={option.value} value={option.value}>
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
