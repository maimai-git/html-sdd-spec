async page=>{
 let checks=0;const ok=(value,message)=>{checks++;if(!value)throw new Error(message)};
 await page.reload();await page.locator('[data-mode="apis"]').click();await page.locator('#catalog [data-record]').first().click();
 const expected=await page.locator('#html-sdd-spec').evaluate(node=>'HTML SDD Spec '+JSON.parse(node.textContent).metadata.title.trim());
 ok(await page.title()===expected,'标签页标题格式错误');
 const id=await page.locator('#detail .card-head .record-id').evaluate(node=>({font:parseFloat(getComputedStyle(node).fontSize),weight:Number(getComputedStyle(node).fontWeight)}));
 ok(id.font<=12&&id.weight<=400,'条目编号仍太显眼');
 const related=page.locator('#detail .related-disclosure');ok(await related.count()>0,'缺少关联编号验证场景');await related.click();
 const styles=await page.locator('#detail .related .tag').evaluateAll(nodes=>nodes.map(node=>({font:parseFloat(getComputedStyle(node).fontSize),weight:Number(getComputedStyle(node).fontWeight)})));
 ok(styles.length>0&&styles.every(x=>x.font<=12&&x.weight<=400),'关联编号仍过大或加粗');
 const parameter=await page.locator('#detail .param-pane .field-name').first().evaluate(node=>({font:parseFloat(getComputedStyle(node).fontSize),weight:Number(getComputedStyle(node).fontWeight)}));
 ok(parameter.font>=14&&parameter.weight>=600,'参数字段被意外缩小');
 await page.locator('[data-mode="plan"]').click();
 const plan=await page.locator('.plan-req').first().evaluate(node=>({font:parseFloat(getComputedStyle(node).fontSize),weight:Number(getComputedStyle(node).fontWeight)}));
 ok(plan.font<=12&&plan.weight<=400,'排期关联需求编号未同步');
 return {checks,offline:true};
}
