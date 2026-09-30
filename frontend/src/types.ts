export interface ColumnInfo {
  column: string
  dtype: string
}

export interface CatalogEntry {
  id: string
  directory_path: string
  file_name: string
  sheet_name: string
  table_name: string
  file_type: 'xlsx' | 'csv'
  row_count: number
  column_schema: ColumnInfo[]
  storage_path: string | null
  uploaded_at: string
  updated_at: string
}

export type DirectoryTree = Record<string, CatalogEntry[]>
