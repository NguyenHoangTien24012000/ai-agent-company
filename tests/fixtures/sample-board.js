// Dữ liệu mẫu độc lập; mốc giờ tương đối giúp kiểm tra tuổi hàng đợi khi mở lại.
(() => {
  const now = Date.now();
  const at = minutes => new Date(now - minutes * 60000).toISOString();
  const makeAsk = (room, number, kind, gate, title, minutes, context, options, recommend) => ({
    id: `${room}-a${number}`, room, kind, gate, title, context, options, recommend,
    links: ['docs/features/' + room.toLowerCase() + '.md'], status: 'open', choice: null,
    note: null, answeredVia: null, createdAt: at(minutes), resolvedAt: null
  });
  const asks = [
    makeAsk('ATTEND', 5, 'duyet', 5, 'Duyệt check cuối: điểm danh + đi muộn', 125,
      '**QA đã kiểm 24 ca**; còn một quyết định về mốc đi muộn.\nLệnh đối chiếu: `python3 -m unittest`. Xem [bản nghiệm thu](docs/acceptance.md).',
      [{key:'ok',label:'Duyệt'},{key:'sua',label:'Cần sửa'}], 'ok'),
    makeAsk('TEAM-STATS', 2, 'quyet', null, 'Chọn cách tính tỷ lệ có mặt', 62,
      'Tính theo **buổi đã diễn ra** hay tất cả buổi trong tháng?\nĐề xuất bỏ các buổi đã huỷ khỏi mẫu số.',
      [{key:'completed',label:'Buổi đã diễn ra'},{key:'all',label:'Tất cả buổi'}], 'completed'),
    makeAsk('PAYMENT', 1, 'thaotac', null, 'Mở app và kiểm tra màn xác nhận', 18,
      'Anh mở app bằng tài khoản thử, vào `Thu phí → Xác nhận`.\nGhi nhận nội dung hiển thị trước khi chốt gói phòng.',
      [{key:'done',label:'Đã kiểm tra'},{key:'blocked',label:'Chưa làm được'}], 'done')
  ];
  const makeBug = (number, status, title, needsBoss = false) => ({
    id:`ATTEND-b${number}`, room:'ATTEND', title, area:number===2?'server':'web',
    steps:'1. Mở danh sách điểm danh.\n2. Chuyển ngày và kiểm tra trạng thái.', shots:[],
    severity:number===1?'high':'normal', status, assignee:number===2?'dev-server':'dev-web', needsBoss,
    history:[{at:at(150-number*8),by:'qa',status:'open',note:'Ghi nhận từ phiên kiểm thử'}],
    createdAt:at(150-number*8), updatedAt:at(number*5)
  });
  const bugs = [makeBug(1,'open','Cần chốt ngưỡng đi muộn',true),makeBug(2,'fixing','Sai tổng khi đổi ngày'),makeBug(3,'retest','Nhãn bị cắt ở màn nhỏ'),makeBug(4,'closed','Thiếu trạng thái rỗng')];
  const room = (key,title,step,roles) => ({
    key,title,status:'active',step,branch:'phong/'+key.toLowerCase(),
    worktree:'/Users/tien/orca/workspaces/sportshub/'+key.toLowerCase(),managerTerminal:'term_'+key.toLowerCase(),
    roles,needsAppKey:key==='ATTEND',lanes:[],asks:asks.filter(ask=>ask.room===key),bugs:[],
    gates:{1:null,2:null,3:null,4:null,5:null,6:null},
    links:{spec:'.scratch/'+key.toLowerCase()+'/spec.md',featureDoc:'docs/features/'+key.toLowerCase()+'.md'},
    overlaps:[],evidence:[],createdAt:at(360),updatedAt:at(5)
  });
  const attend=room('ATTEND','Điểm danh & đi muộn','cho-check',['techlead','dev-server','dev-web','qa','review']);
  attend.bugs=bugs;
  for(const gate of [1,2,3,4])attend.gates[gate]={at:at(240-gate*20),choice:'ok',askId:'ATTEND-a'+gate};
  attend.lanes=[{role:'dev-server',handle:'term_attend_server',model:'gpt-6-astra',status:'running',note:'Sửa tổng khi đổi ngày',updatedAt:at(8)},{role:'dev-web',handle:'term_attend_web',model:'gpt-6-astra',status:'done',note:'Đã sửa màn nhỏ',updatedAt:at(10)},{role:'qa',handle:'term_attend_qa',model:'opus',status:'waiting',note:'Chờ build để kiểm lại',updatedAt:at(4)}];
  attend.links.qaReport='docs/qa-report.md';
  attend.evidence=[{claim:'24 ca kiểm tra đạt; bản ghi QA khớp',manager:'24/24 đạt',thuKy:'Đã đọc lại output: 24/24',cmd:'python3 -m unittest discover',ok:true,at:at(12)}];
  const stats=room('TEAM-STATS','Thống kê hoạt động đội','thiet-ke',['designer','techlead','dev-web','qa']);
  stats.gates[1]={at:at(170),choice:'ok',askId:'TEAM-STATS-a1'};
  stats.lanes=[{role:'designer',handle:'term_stats_design',model:'opus',status:'running',note:'Bố cục tổng quan tháng',updatedAt:at(3)},{role:'techlead',handle:'term_stats_lead',model:'opus',status:'waiting',note:'Chờ chọn cách tính tỷ lệ',updatedAt:at(7)}];
  stats.evidence=[{claim:'Số liệu tổng còn lệch giữa hai cách tính',manager:'Tỷ lệ 85%',thuKy:'Tính lại từ mẫu: 80%',cmd:'python3 scripts/check_stats.py',ok:false,at:at(20)}];
  attend.overlaps=[{with:'TEAM-STATS',files:['web/src/app/router.tsx'],conflict:false,at:at(40)}];
  stats.overlaps=[{with:'ATTEND',files:['web/src/app/router.tsx'],conflict:false,at:at(40)}];
  const payment=room('PAYMENT','Thu phí thành viên','hoi-dap',['designer','techlead']);
  payment.lanes=[{role:'techlead',handle:'term_payment_lead',model:'opus',status:'waiting',note:'Chờ anh kiểm tra app',updatedAt:at(18)}];
  const eventTypes=['room_opened','room_changed','lane_changed','ask_opened','key_taken','bug_opened','bug_changed','overlap','evidence','ask_resolved','lane_changed','note','ask_opened','bug_changed','evidence'];
  window.BOARD={generatedAt:at(0),appKey:{room:'ATTEND',since:at(95)},rooms:[attend,stats,payment],
    myQueue:[asks[2],asks[0],bugs[0],asks[1]],
    events:eventTypes.map((type,index)=>({ts:at(150-index*10),type,room:['ATTEND','TEAM-STATS','PAYMENT'][index%3],note:['Khởi tạo hồ sơ phòng','Cập nhật tiến độ','Đã đối chiếu với Manager'][index%3]})).reverse()};
})();
