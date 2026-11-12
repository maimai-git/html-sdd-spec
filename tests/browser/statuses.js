async page=>{
 let checks=0;const ok=(value,message)=>{checks++;if(!value)throw new Error(message)};
 await page.setViewportSize({width:1600,height:1050});await page.reload();
 const expected=['rgb(22, 101, 52)','rgb(29, 78, 216)','rgb(133, 77, 14)','rgb(109, 40, 217)','rgb(180, 35, 24)','rgb(71, 85, 105)'];
 for(const mode of ['requirements','apis','tables','architecture','configs','plan']){
  await page.locator('[data-mode="'+mode+'"]').click();
  ok(await page.locator('#documentState').textContent()==='开发中','页头阶段随分类改变');
  ok(await page.locator('#documentState').evaluate(node=>getComputedStyle(node).color)==='rgb(29, 78, 216)','页头颜色随分类改变');
 }
 for(let i=0;i<6;i++){
  const node=page.locator('tr[data-plan-id="PLAN-COLOR-'+i+'"] .status').first();
  ok(await node.evaluate(n=>getComputedStyle(n).color)===expected[i],'状态色不一致 '+i);
 }
 await page.locator('[data-mode="apis"]').click();
 ok((await page.locator('#detail').innerText()).includes('代码完成仍需部署'),'状态说明丢失');
 ok(await page.locator('#detail .tag-list .status').first().textContent()==='部分完成','开发状态与部署状态混淆');
 await page.locator('[data-mode="requirements"]').click();await page.locator('.acceptance-disclosure').click();
 ok((await page.locator('.acceptance-disclosure').innerText()).includes('已通过'),'验收状态错误');
 return {checks,offline:true};
}
