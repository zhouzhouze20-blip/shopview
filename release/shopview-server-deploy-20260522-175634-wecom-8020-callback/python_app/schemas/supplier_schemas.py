from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SupplierCreate(BaseModel):
    sbid: str
    sbcname: str
    sbsname: Optional[str] = None
    sbstatus: str = "Y"
    sbflag: str = "Y"
    sbregcode: str = "DEFAULT"
    sbcatcode: str = "DEFAULT"
    sbtaxpayer: str = "N"
    sblxr: Optional[str] = None
    sblxfs: Optional[str] = None
    sbtel: Optional[str] = None
    sbemail: Optional[str] = None
    sbtaxno: Optional[str] = None
    sbbank: Optional[str] = None
    sbaccntno: Optional[str] = None
    sbaddr: Optional[str] = None
    sbfrdb: Optional[str] = None
    sbyjcgy: Optional[str] = None
    grade: Optional[str] = None
    sbnbtype: Optional[str] = None
    sbiftt: Optional[str] = None
    sbcomname: Optional[str] = None
    sbcomename: Optional[str] = None
    sbyt: Optional[str] = None
    sbxfdx: Optional[str] = None
    sbyxmf: Optional[str] = None
    sbyxrent: Optional[float] = None
    sbyxmon: Optional[float] = None
    sbyxmj: Optional[float] = None
    sbopendesc: Optional[str] = None
    sbppdesc: Optional[str] = None
    sbjfyq: Optional[str] = None
    sbmemo: Optional[str] = None
    sbwmid1: str = "N"
    sbwmid2: str = "N"
    sbwmid3: str = "N"
    sbwmid4: str = "N"
    sbwmid5: str = "N"
    sbjszq: float = 0
    sbdhzq: int = 0
    sbdbsend: str = "N"
    sblry: str = "system"


class SupplierUpdate(BaseModel):
    sbcname: Optional[str] = None
    sbsname: Optional[str] = None
    sbstatus: Optional[str] = None
    sbflag: Optional[str] = None
    sbregcode: Optional[str] = None
    sbcatcode: Optional[str] = None
    sbtaxpayer: Optional[str] = None
    sblxr: Optional[str] = None
    sblxfs: Optional[str] = None
    sbtel: Optional[str] = None
    sbemail: Optional[str] = None
    sbtaxno: Optional[str] = None
    sbbank: Optional[str] = None
    sbaccntno: Optional[str] = None
    sbaddr: Optional[str] = None
    sbfrdb: Optional[str] = None
    sbyjcgy: Optional[str] = None
    grade: Optional[str] = None
    sbnbtype: Optional[str] = None
    sbiftt: Optional[str] = None
    sbcomname: Optional[str] = None
    sbcomename: Optional[str] = None
    sbyt: Optional[str] = None
    sbxfdx: Optional[str] = None
    sbyxmf: Optional[str] = None
    sbyxrent: Optional[float] = None
    sbyxmon: Optional[float] = None
    sbyxmj: Optional[float] = None
    sbopendesc: Optional[str] = None
    sbppdesc: Optional[str] = None
    sbjfyq: Optional[str] = None
    sbmemo: Optional[str] = None
    sbwmid1: Optional[str] = None
    sbwmid2: Optional[str] = None
    sbwmid3: Optional[str] = None
    sbwmid4: Optional[str] = None
    sbwmid5: Optional[str] = None
    sbjszq: Optional[float] = None
    sbdhzq: Optional[int] = None
    sbdbsend: Optional[str] = None
    sbxgr: Optional[str] = None


class SupplierListItem(BaseModel):
    sbid: str
    sbcname: str
    sbaddr: Optional[str] = None
    sbstatus: Optional[str] = None
    sbflag: Optional[str] = None
    sbcatcode: Optional[str] = None
    sbregcode: Optional[str] = None
    sbfrdb: Optional[str] = None
    sbbank: Optional[str] = None
    sbaccntno: Optional[str] = None
    sbtaxno: Optional[str] = None
    sblrrq: Optional[datetime] = None
    sbxgrq: Optional[datetime] = None


class SupplierDetail(BaseModel):
    sbid: str
    sbcname: str
    sbsname: Optional[str] = None
    sbstatus: Optional[str] = None
    sbflag: Optional[str] = None
    sbregcode: Optional[str] = None
    sbcatcode: Optional[str] = None
    sbtaxpayer: Optional[str] = None
    sblxr: Optional[str] = None
    sblxfs: Optional[str] = None
    sbtel: Optional[str] = None
    sbemail: Optional[str] = None
    sbtaxno: Optional[str] = None
    sbbank: Optional[str] = None
    sbaccntno: Optional[str] = None
    sbaddr: Optional[str] = None
    sbfrdb: Optional[str] = None
    sbyjcgy: Optional[str] = None
    grade: Optional[str] = None
    sbnbtype: Optional[str] = None
    sbiftt: Optional[str] = None
    sbcomname: Optional[str] = None
    sbcomename: Optional[str] = None
    sbyt: Optional[str] = None
    sbxfdx: Optional[str] = None
    sbyxmf: Optional[str] = None
    sbyxrent: Optional[float] = None
    sbyxmon: Optional[float] = None
    sbyxmj: Optional[float] = None
    sbopendesc: Optional[str] = None
    sbppdesc: Optional[str] = None
    sbjfyq: Optional[str] = None
    sbmemo: Optional[str] = None
    sbwmid1: Optional[str] = None
    sbwmid2: Optional[str] = None
    sbwmid3: Optional[str] = None
    sbwmid4: Optional[str] = None
    sbwmid5: Optional[str] = None
    sbjszq: Optional[float] = None
    sbdhzq: Optional[int] = None
    sbdbsend: Optional[str] = None
    sblry: Optional[str] = None
    sbljsrq: Optional[datetime] = None
    sblrrq: Optional[datetime] = None
    sbxgr: Optional[str] = None
    sbxgrq: Optional[datetime] = None
