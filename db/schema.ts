// The deployed game does not require a request-time application database.
// Its generated JSON comes from the DuckDB + dbt warehouse under /warehouse.
// Add Drizzle/D1 tables here only if a future product feature needs transactional state.
export {};
