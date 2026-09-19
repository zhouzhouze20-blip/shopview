"""PAPI task definition only; no scheduler or ERP calls in the web application."""
FIELDS='batch_id row_kind source_key source_at source_hash store_code supplier_code receipt_number batch_rows linked_rows settlement_number source_status expected_rows expected_hash'.split()


def extraction_sql():
    return '''WITH grouped AS (
      SELECT TRIM(SSBMMKT) store_code,TRIM(SSBSUPID) supplier_code,TRIM(SSBBILLNO) receipt_number,
        COUNT(*) batch_rows,SUM(CASE WHEN TRIM(SSBJSBILLNO) IS NOT NULL THEN 1 ELSE 0 END) linked_rows,
        MIN(TRIM(SSBJSBILLNO)) settlement_number,MIN(TRIM(SSBSTATUS)) source_status
      FROM DBUSRMKT.SETTLESUPBATCH WHERE SSBMMKT IN ('601','602','603')
        AND TRIM(SSBSUPID) IS NOT NULL AND TRIM(SSBBILLNO) IS NOT NULL
      GROUP BY TRIM(SSBMMKT),TRIM(SSBSUPID),TRIM(SSBBILLNO)
    ), hashed AS (
      SELECT g.*,ORA_HASH(store_code||':'||supplier_code||':'||receipt_number||':'||
        TO_CHAR(batch_rows)||':'||TO_CHAR(linked_rows)||':'||NVL(settlement_number,'-')||':'||NVL(source_status,'-')) source_hash
      FROM grouped g
    ), data_rows AS (
      SELECT 'data' row_kind,store_code||':'||supplier_code||':'||receipt_number source_key,
        store_code,supplier_code,receipt_number,batch_rows,linked_rows,settlement_number,source_status,source_hash FROM hashed
      UNION ALL
      SELECT 'manifest','-',NULL,NULL,NULL,NULL,NULL,NULL,NULL,0 FROM DUAL
    ) SELECT 'receipts-'||TO_CHAR(SYSDATE,'YYYYMMDDHH24MISS') AS "batch_id",
      row_kind AS "row_kind",source_key AS "source_key",
      TO_CHAR(SYSDATE,'YYYY-MM-DD HH24:MI:SS')||' +08:00' AS "source_at",
      source_hash AS "source_hash",store_code AS "store_code",supplier_code AS "supplier_code",
      receipt_number AS "receipt_number",batch_rows AS "batch_rows",linked_rows AS "linked_rows",
      settlement_number AS "settlement_number",source_status AS "source_status",
      CASE WHEN row_kind='manifest' THEN SUM(CASE WHEN row_kind='data' THEN 1 ELSE 0 END) OVER() END AS "expected_rows",
      CASE WHEN row_kind='manifest' THEN SUM(source_hash) OVER() END AS "expected_hash"
      FROM data_rows ORDER BY CASE row_kind WHEN 'data' THEN 0 ELSE 1 END,source_key'''


def task_body(enabled=False):
    return dict(name='化妆品配票-三店验收结算关联全量同步',sourceId=5,targetSourceId=4,
        sqlText=extraction_sql(),tableName='public.cosmetics_receipt_settlement_stage',
        fieldMapping={f:f for f in FIELDS},insertMode='insert',keyColumns='batch_id,row_kind,source_key',
        batchSize=3000,maxRows=0,autoCreateTable=False,resumeEnabled=False,
        queryTimeoutSeconds=120,dbTimeoutSeconds=120,maxRuntimeSeconds=600,
        enabled=enabled,scheduleEnabled=enabled,scheduleType='interval',scheduleIntervalMinutes=15,
        scheduleTime='00:00',scheduleWeekdays='0,1,2,3,4,5,6',scheduleMonthDay=1)
