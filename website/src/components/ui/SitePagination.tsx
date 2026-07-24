import { useEffect, useMemo, useState, type MouseEvent } from "react";

import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import {
  ACADEMY_LIST_PAGE_SIZE,
  buildAcademyListUrl,
  parseAcademyListCategory,
  parseAcademyListSearch,
} from "@/lib/academy/pagination";
import {
  BLOG_LIST_PAGE_SIZE,
  buildAuthorListUrl,
  buildBlogListUrl,
  parseBlogListCategory,
  parseBlogListSearch,
} from "@/lib/blog/pagination";
import { getPageItems, parseListPage } from "@/lib/pagination";
import {
  RESEARCH_LIST_PAGE_SIZE,
  buildResearchListUrl,
  readResearchListCategory,
} from "@/lib/research/pagination";

export type SitePaginationKind = "blog" | "author" | "research" | "academy";

type Props = {
  kind: SitePaginationKind;
  authorSlug?: string;
};

type ListConfig = {
  pageSize: number;
  ariaLabel: string;
  className: string;
  hasSearch: boolean;
  hasCategory: boolean;
  /** research：没有分类按钮时不启用 */
  requireCategoryFilters: boolean;
  categoryActiveAttr: "aria-current" | "aria-selected";
  selectors: {
    card: string;
    categoryFilter: string;
    searchForm?: string;
    searchInput?: string;
    empty?: string;
  };
  dataset: {
    cardCategory: string;
    cardTitle?: string;
    cardDescription?: string;
    categoryFilter: string;
  };
  parseCategory: (params: URLSearchParams) => string;
  parseSearch: (params: URLSearchParams) => string;
  buildUrl: (page: number, category: string, search: string) => string;
};

function configFor(kind: SitePaginationKind, authorSlug: string): ListConfig {
  if (kind === "author") {
    return {
      pageSize: BLOG_LIST_PAGE_SIZE,
      ariaLabel: "博客分页",
      className: "blog-pagination",
      hasSearch: false,
      hasCategory: false,
      requireCategoryFilters: false,
      categoryActiveAttr: "aria-current",
      selectors: {
        card: "[data-blog-card]",
        categoryFilter: "[data-blog-category-filter]",
        empty: "[data-blog-grid-empty]",
      },
      dataset: {
        cardCategory: "blogCardCategory",
        categoryFilter: "blogCategoryFilter",
      },
      parseCategory: () => "all",
      parseSearch: () => "",
      buildUrl: (page) => buildAuthorListUrl(authorSlug, page),
    };
  }

  if (kind === "research") {
    return {
      pageSize: RESEARCH_LIST_PAGE_SIZE,
      ariaLabel: "报告分页",
      className: "research-pagination",
      hasSearch: false,
      hasCategory: true,
      requireCategoryFilters: true,
      categoryActiveAttr: "aria-selected",
      selectors: {
        card: "[data-research-card]",
        categoryFilter: "[data-research-category-filter]",
      },
      dataset: {
        cardCategory: "researchCardCategory",
        categoryFilter: "researchCategoryFilter",
      },
      parseCategory: readResearchListCategory,
      parseSearch: () => "",
      buildUrl: (page, category) => buildResearchListUrl(page, category),
    };
  }

  if (kind === "academy") {
    return {
      pageSize: ACADEMY_LIST_PAGE_SIZE,
      ariaLabel: "学院分页",
      className: "academy-pagination",
      hasSearch: true,
      hasCategory: true,
      requireCategoryFilters: false,
      categoryActiveAttr: "aria-current",
      selectors: {
        card: "[data-academy-card]",
        categoryFilter: "[data-academy-category-filter]",
        searchForm: "[data-academy-search-form]",
        searchInput: "[data-academy-search-input]",
        empty: "[data-academy-grid-empty]",
      },
      dataset: {
        cardCategory: "academyCardCategory",
        cardTitle: "academyCardTitle",
        cardDescription: "academyCardDescription",
        categoryFilter: "academyCategoryFilter",
      },
      parseCategory: parseAcademyListCategory,
      parseSearch: parseAcademyListSearch,
      buildUrl: buildAcademyListUrl,
    };
  }

  return {
    pageSize: BLOG_LIST_PAGE_SIZE,
    ariaLabel: "博客分页",
    className: "blog-pagination",
    hasSearch: true,
    hasCategory: true,
    requireCategoryFilters: false,
    categoryActiveAttr: "aria-current",
    selectors: {
      card: "[data-blog-card]",
      categoryFilter: "[data-blog-category-filter]",
      searchForm: "[data-blog-search-form]",
      searchInput: "[data-blog-search-input]",
      empty: "[data-blog-grid-empty]",
    },
    dataset: {
      cardCategory: "blogCardCategory",
      cardTitle: "blogCardTitle",
      cardDescription: "blogCardDescription",
      categoryFilter: "blogCategoryFilter",
    },
    parseCategory: parseBlogListCategory,
    parseSearch: parseBlogListSearch,
    buildUrl: buildBlogListUrl,
  };
}

function readDataset(el: HTMLElement, key: string): string {
  return (el.dataset as Record<string, string | undefined>)[key] ?? "";
}

type PaginationBarProps = {
  page: number;
  totalPages: number;
  hrefForPage: (page: number) => string;
  onPageChange: (page: number) => void;
  "aria-label"?: string;
  className?: string;
};

function PaginationBar({
  page,
  totalPages,
  hrefForPage,
  onPageChange,
  "aria-label": ariaLabel = "分页",
  className,
}: PaginationBarProps) {
  if (totalPages <= 1) return null;

  const goTo = (next: number) => (event: MouseEvent) => {
    event.preventDefault();
    onPageChange(next);
  };

  return (
    <Pagination totalPages={totalPages} aria-label={ariaLabel} className={className}>
      <PaginationContent>
        <PaginationItem>
          <PaginationPrevious
            href={page > 1 ? hrefForPage(page - 1) : undefined}
            disabled={page <= 1}
            onClick={page > 1 ? goTo(page - 1) : undefined}
          />
        </PaginationItem>

        {getPageItems(page, totalPages).map((item, index) => (
          <PaginationItem key={item === "ellipsis" ? `ellipsis-${index}` : item}>
            {item === "ellipsis" ? (
              <PaginationEllipsis />
            ) : (
              <PaginationLink
                href={hrefForPage(item)}
                isActive={item === page}
                onClick={goTo(item)}
              >
                {item}
              </PaginationLink>
            )}
          </PaginationItem>
        ))}

        <PaginationItem>
          <PaginationNext
            href={page < totalPages ? hrefForPage(page + 1) : undefined}
            disabled={page >= totalPages}
            onClick={page < totalPages ? goTo(page + 1) : undefined}
          />
        </PaginationItem>
      </PaginationContent>
    </Pagination>
  );
}

/** 官网列表客户端分页：博客 / 作者 / 报告 / 学院共用 */
export default function SitePagination({ kind, authorSlug = "" }: Props) {
  const config = useMemo(() => configFor(kind, authorSlug), [kind, authorSlug]);

  const [enabled, setEnabled] = useState(!config.requireCategoryFilters);
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState("all");
  const [search, setSearch] = useState("");
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    if (config.requireCategoryFilters) {
      const hasFilters = document.querySelectorAll(config.selectors.categoryFilter).length > 0;
      setEnabled(hasFilters);
      if (!hasFilters) return;
    } else {
      setEnabled(true);
    }

    const params = new URLSearchParams(window.location.search);
    setPage(parseListPage(params.get("page")));
    setCategory(config.hasCategory ? config.parseCategory(params) : "all");
    setSearch(config.hasSearch ? config.parseSearch(params) : "");

    if (config.hasSearch && config.selectors.searchInput) {
      const searchInput = document.querySelector<HTMLInputElement>(config.selectors.searchInput);
      if (searchInput) {
        searchInput.value = config.parseSearch(params);
      }
    }
  }, [config]);

  useEffect(() => {
    if (!enabled || !config.hasCategory) return;

    const filters = document.querySelectorAll<HTMLElement>(config.selectors.categoryFilter);
    const onClick = (event: Event) => {
      event.preventDefault();
      const target = event.currentTarget as HTMLElement;
      setCategory(readDataset(target, config.dataset.categoryFilter) || "all");
      setPage(1);
    };
    filters.forEach((el) => el.addEventListener("click", onClick));
    return () => filters.forEach((el) => el.removeEventListener("click", onClick));
  }, [enabled, config]);

  useEffect(() => {
    if (!enabled || !config.hasSearch || !config.selectors.searchForm) return;

    const form = document.querySelector<HTMLFormElement>(config.selectors.searchForm);
    const input = config.selectors.searchInput
      ? document.querySelector<HTMLInputElement>(config.selectors.searchInput)
      : null;
    if (!form) return;

    const onSubmit = (event: Event) => {
      event.preventDefault();
      setSearch(input?.value ?? "");
      setPage(1);
    };
    form.addEventListener("submit", onSubmit);
    return () => form.removeEventListener("submit", onSubmit);
  }, [enabled, config]);

  useEffect(() => {
    if (!enabled) return;

    const onPopState = () => {
      const params = new URLSearchParams(window.location.search);
      const nextSearch = config.hasSearch ? config.parseSearch(params) : "";
      if (config.hasSearch && config.selectors.searchInput) {
        const searchInput = document.querySelector<HTMLInputElement>(config.selectors.searchInput);
        if (searchInput) searchInput.value = nextSearch;
      }
      setPage(parseListPage(params.get("page")));
      setCategory(config.hasCategory ? config.parseCategory(params) : "all");
      setSearch(nextSearch);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [enabled, config]);

  useEffect(() => {
    if (!enabled) return;

    const cards = [...document.querySelectorAll<HTMLElement>(config.selectors.card)];
    const normalizedSearch = search.trim().toLowerCase();

    const matchedCards = cards.filter((card) => {
      const cardCategory = readDataset(card, config.dataset.cardCategory);
      const categoryMatch =
        !config.hasCategory || category === "all" || cardCategory === category;
      if (!categoryMatch) return false;
      if (!config.hasSearch || !normalizedSearch) return true;
      const haystack = [
        config.dataset.cardTitle ? readDataset(card, config.dataset.cardTitle) : "",
        config.dataset.cardDescription ? readDataset(card, config.dataset.cardDescription) : "",
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(normalizedSearch);
    });

    const nextTotalPages = Math.max(1, Math.ceil(matchedCards.length / config.pageSize));
    const safePage = Math.min(Math.max(1, page), nextTotalPages);
    const start = (safePage - 1) * config.pageSize;

    cards.forEach((card) => card.classList.add("is-hidden"));
    matchedCards.slice(start, start + config.pageSize).forEach((card) => {
      card.classList.remove("is-hidden");
    });

    if (config.selectors.empty) {
      const emptyEl = document.querySelector<HTMLElement>(config.selectors.empty);
      if (emptyEl) emptyEl.hidden = matchedCards.length > 0;
    }

    if (config.hasCategory) {
      document.querySelectorAll<HTMLElement>(config.selectors.categoryFilter).forEach((el) => {
        const isActive = (readDataset(el, config.dataset.categoryFilter) || "all") === category;
        el.classList.toggle("is-active", isActive);
        if (config.categoryActiveAttr === "aria-selected") {
          el.setAttribute("aria-selected", isActive ? "true" : "false");
        } else if (isActive) {
          el.setAttribute("aria-current", "page");
        } else {
          el.removeAttribute("aria-current");
        }
      });
    }

    setTotalPages(nextTotalPages);
    if (safePage !== page) {
      setPage(safePage);
      return;
    }

    const nextUrl = config.buildUrl(safePage, category, search);
    if (`${window.location.pathname}${window.location.search}` !== nextUrl) {
      history.replaceState(null, "", nextUrl);
    }
  }, [enabled, page, category, search, config]);

  if (!enabled) return null;

  return (
    <PaginationBar
      page={page}
      totalPages={totalPages}
      hrefForPage={(nextPage) => config.buildUrl(nextPage, category, search)}
      onPageChange={setPage}
      aria-label={config.ariaLabel}
      className={config.className}
    />
  );
}
