import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination"

type TablePaginationProps = {
  page: number
  totalPages: number
  total: number
  pageSize: number
  basePath: string
  pageParam?: string
  query?: Record<string, string | number | undefined>
}

function pageHref(
  basePath: string,
  pageParam: string,
  page: number,
  query: Record<string, string | number | undefined>
) {
  const params = new URLSearchParams()

  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== "") {
      params.set(key, String(value))
    }
  }
  params.set(pageParam, String(page))

  return `${basePath}?${params.toString()}`
}

export function TablePagination({
  page,
  totalPages,
  total,
  pageSize,
  basePath,
  pageParam = "page",
  query = {},
}: TablePaginationProps) {
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1
  const end = Math.min(page * pageSize, total)
  const pages = Array.from(
    { length: Math.min(5, totalPages) },
    (_, index) => {
      const first = Math.max(1, Math.min(page - 2, totalPages - 4))
      return first + index
    }
  )

  return (
    <div className="mt-4 flex flex-col gap-3 border-t border-border pt-4 sm:flex-row sm:items-center sm:justify-between">
      <p className="text-sm text-muted-foreground">
        显示 {start}-{end} 条，共 {total} 条，每页 {pageSize} 条
      </p>
      <Pagination className="mx-0 w-auto justify-end">
        <PaginationContent>
          <PaginationItem>
            <PaginationPrevious
              href={pageHref(
                basePath,
                pageParam,
                Math.max(1, page - 1),
                query
              )}
              aria-disabled={page <= 1}
              className={page <= 1 ? "pointer-events-none opacity-50" : ""}
            />
          </PaginationItem>
          {pages.map((item) => (
            <PaginationItem key={item}>
              <PaginationLink
                href={pageHref(basePath, pageParam, item, query)}
                isActive={item === page}
              >
                {item}
              </PaginationLink>
            </PaginationItem>
          ))}
          <PaginationItem>
            <PaginationNext
              href={pageHref(
                basePath,
                pageParam,
                Math.min(totalPages, page + 1),
                query
              )}
              aria-disabled={page >= totalPages}
              className={page >= totalPages ? "pointer-events-none opacity-50" : ""}
            />
          </PaginationItem>
        </PaginationContent>
      </Pagination>
    </div>
  )
}
