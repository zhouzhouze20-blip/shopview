/** Local review fixture only. Never loaded by the production entry point. */
import React from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/contexts/AuthContext";
import CosmeticsPaymentMatchingPage from "@/pages/cosmetics-payment-matching";
import "../index.css";
const invoiceRows = Array.from({ length: 11 }, (_, i) => ({source_key:`I${i}`,version:"a".repeat(64),number:`260920000000${String(i+1).padStart(5,"0")}`,date:i<5?"2026-07-16":"2026-08-21",amount:"100.00",remark:i<5?"迪奥香水 七月进货":i===5?null:"娇兰 八月进货"}));
const receiptRows = Array.from({length: 2},(_,i)=>({source_key:`R${i}`,version:"a".repeat(64),number:`60140426080${i+1}`,date:i===0?"2026-07-29":"2026-08-20",amount:"550.00",settlement_status:"未关联结算单",supplier_code:"DEMO001",supplier_name:"示例化妆品供应商",groups:[`601010${i+1}`],group_names:`601010${i+1} 美妆柜组`}));
let saved: any[]=[];
const nativeFetch=window.fetch.bind(window);
window.fetch=async (input, init)=>{
 const url=String(input);
 let data:any;
 if(url.includes("/api/auth/me")) data={user_id:1,username:"preview",real_name:"预览业务员",status:"active",is_active:true,role_codes:[],role_names:[],permission_codes:["settlement.cosmetics_matching.view","settlement.cosmetics_matching.create"]};
 else if(url.includes("/api/cosmetics-payment-matching")){
  if(init?.method==="POST") {data={number:"PP202608-PREVIEW000001",invoice_amount:"1100.00",receipt_amount:"1100.00",difference:"0.00",invoices:invoiceRows,receipts:receiptRows};saved=[data];}
  else if(url.includes("/suppliers"))data={items:[{code:"DEMO001",name:"示例化妆品供应商"}],has_more:false};
  else if(url.includes("/history"))data={items:saved};
  else data={settlement_sync:{source_at:new Date().toISOString(),stale:new URLSearchParams(location.search).has("stale")},invoices:saved.length?[]:invoiceRows,receipts:saved.length?[]:receiptRows,groups:["6010101","6010102"],group_options:[{code:"6010101",name:"Christian Dior迪奥厅"},{code:"6010102",name:"Guerlain娇兰厅"}],buyer_name:"常州百货大楼股份有限公司",note:"预览使用模拟数据，不写入真实配票记录。"};
 }else return nativeFetch(input,init);
 return new Response(JSON.stringify(data),{status:200,headers:{"Content-Type":"application/json"}});
};
createRoot(document.getElementById("root")!).render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><AuthProvider><div className="bg-amber-50 px-6 py-2 text-sm text-amber-900">交互预览 · 模拟数据 · 可试选11张发票与2张验收单</div><CosmeticsPaymentMatchingPage /></AuthProvider></QueryClientProvider>);
