-- 自营销售专用表，不修改现有百货销售数据。

CREATE TABLE IF NOT EXISTS self_operated_sales_imports (
	id SERIAL NOT NULL,
	source_file VARCHAR(255) NOT NULL,
	sha256 VARCHAR(64) NOT NULL,
	channel VARCHAR(50) NOT NULL,
	section VARCHAR(20) NOT NULL,
	start_date DATE NOT NULL,
	end_date DATE NOT NULL,
	imported_at TIMESTAMP WITH TIME ZONE NOT NULL,
	imported_by VARCHAR(100),
	row_count INTEGER NOT NULL,
	sales NUMERIC(18, 2) NOT NULL,
	PRIMARY KEY (id)
)

;


CREATE TABLE IF NOT EXISTS self_operated_sales_coverage (
	section VARCHAR(20) NOT NULL,
	channel VARCHAR(50) NOT NULL,
	business_date DATE NOT NULL,
	import_id INTEGER NOT NULL,
	PRIMARY KEY (section, channel, business_date),
	FOREIGN KEY(import_id) REFERENCES self_operated_sales_imports (id)
)

;


CREATE TABLE IF NOT EXISTS self_operated_sales_lines (
	id SERIAL NOT NULL,
	import_id INTEGER NOT NULL,
	source_row INTEGER NOT NULL,
	section VARCHAR(20) NOT NULL,
	channel VARCHAR(50) NOT NULL,
	business_date DATE NOT NULL,
	bill VARCHAR(100) NOT NULL,
	original_bill VARCHAR(100),
	product VARCHAR(100) NOT NULL,
	product_name VARCHAR(255),
	color VARCHAR(100),
	size VARCHAR(100),
	sale_type VARCHAR(20) NOT NULL,
	quantity NUMERIC(18, 4) NOT NULL,
	sales NUMERIC(18, 2) NOT NULL,
	discount NUMERIC(12, 8) NOT NULL,
	supplier_rate NUMERIC(6, 4) NOT NULL,
	supplier_cost NUMERIC(18, 2) NOT NULL,
	venue_fee NUMERIC(18, 2) NOT NULL,
	expected_receipt NUMERIC(18, 2) NOT NULL,
	gross_profit NUMERIC(18, 2) NOT NULL,
	source_data JSONB NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(import_id) REFERENCES self_operated_sales_imports (id)
)

;
CREATE INDEX IF NOT EXISTS ix_self_operated_sales_scope_date ON self_operated_sales_lines (section, channel, business_date);
