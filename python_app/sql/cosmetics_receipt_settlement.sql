CREATE TABLE IF NOT EXISTS public.cosmetics_receipt_settlement_state (
 store_code text NOT NULL, supplier_code text NOT NULL, receipt_number text NOT NULL,
 batch_rows bigint NOT NULL CHECK(batch_rows>0), linked_rows bigint NOT NULL CHECK(linked_rows>=0 AND linked_rows<=batch_rows),
 settlement_number text, source_status text,
 PRIMARY KEY(store_code,supplier_code,receipt_number)
);
CREATE TABLE IF NOT EXISTS public.cosmetics_receipt_settlement_sync (
 singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton), batch_id text NOT NULL,
 source_at timestamptz NOT NULL, published_at timestamptz NOT NULL,
 row_count bigint NOT NULL, hash_sum numeric NOT NULL
);
CREATE TABLE IF NOT EXISTS public.cosmetics_receipt_settlement_stage (
 batch_id text NOT NULL, row_kind text NOT NULL CHECK(row_kind IN ('data','manifest')),
 source_key text NOT NULL, source_at timestamptz NOT NULL, source_hash numeric NOT NULL,
 store_code text, supplier_code text, receipt_number text,
 batch_rows bigint, linked_rows bigint, settlement_number text, source_status text,
 expected_rows bigint, expected_hash numeric,
 PRIMARY KEY(batch_id,row_kind,source_key),
 CHECK(row_kind<>'data' OR (store_code IS NOT NULL AND store_code IN ('601','602','603') AND supplier_code IS NOT NULL AND receipt_number IS NOT NULL AND batch_rows IS NOT NULL AND linked_rows IS NOT NULL AND batch_rows>0 AND linked_rows>=0 AND linked_rows<=batch_rows)),
 CHECK(row_kind<>'manifest' OR (source_key='-' AND expected_rows IS NOT NULL AND expected_rows>=0 AND expected_hash IS NOT NULL))
);
CREATE OR REPLACE FUNCTION public.publish_cosmetics_receipt_settlement()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
DECLARE m record; n bigint; h numeric;
BEGIN
 FOR m IN SELECT * FROM new_rows WHERE row_kind='manifest' LOOP
  PERFORM pg_advisory_xact_lock(862034,1);
  SELECT count(*),coalesce(sum(source_hash),0) INTO n,h
   FROM public.cosmetics_receipt_settlement_stage WHERE batch_id=m.batch_id AND row_kind='data';
  IF n<>m.expected_rows OR h<>m.expected_hash THEN
   RAISE EXCEPTION 'Receipt settlement snapshot incomplete or checksum mismatch';
  END IF;
  IF EXISTS(SELECT 1 FROM public.cosmetics_receipt_settlement_stage WHERE batch_id=m.batch_id AND
     (source_at<>m.source_at OR (row_kind='data' AND source_key<>store_code||':'||supplier_code||':'||receipt_number))) THEN
   RAISE EXCEPTION 'Receipt settlement snapshot scope/key mismatch';
  END IF;
  IF EXISTS(SELECT 1 FROM public.cosmetics_receipt_settlement_sync WHERE source_at>=m.source_at) THEN
   RAISE EXCEPTION 'Receipt settlement snapshot is not newer';
  END IF;
  DELETE FROM public.cosmetics_receipt_settlement_state;
  INSERT INTO public.cosmetics_receipt_settlement_state
   SELECT store_code,supplier_code,receipt_number,batch_rows,linked_rows,settlement_number,source_status
   FROM public.cosmetics_receipt_settlement_stage WHERE batch_id=m.batch_id AND row_kind='data';
  INSERT INTO public.cosmetics_receipt_settlement_sync VALUES(true,m.batch_id,m.source_at,clock_timestamp(),n,h)
   ON CONFLICT(singleton) DO UPDATE SET batch_id=excluded.batch_id,source_at=excluded.source_at,
    published_at=excluded.published_at,row_count=excluded.row_count,hash_sum=excluded.hash_sum;
  DELETE FROM public.cosmetics_receipt_settlement_stage WHERE source_at<=m.source_at;
 END LOOP;
 RETURN NULL;
END $$;
DROP TRIGGER IF EXISTS cosmetics_receipt_settlement_publish ON public.cosmetics_receipt_settlement_stage;
CREATE TRIGGER cosmetics_receipt_settlement_publish AFTER INSERT ON public.cosmetics_receipt_settlement_stage
 REFERENCING NEW TABLE AS new_rows FOR EACH STATEMENT EXECUTE FUNCTION public.publish_cosmetics_receipt_settlement();
