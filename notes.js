const topicSearch=document.querySelector('#topic-search');
topicSearch?.addEventListener('input',()=>{const query=topicSearch.value.trim().toLowerCase();let count=0;document.querySelectorAll('[data-topic]').forEach(topic=>{topic.hidden=!topic.dataset.topic.toLowerCase().includes(query);if(!topic.hidden)count++;});document.querySelector('#topic-empty').hidden=count>0;});
const skillSearch=document.querySelector('#skill-search');
const skillTotal=document.querySelectorAll('.skill-group tbody tr').length;
let filter='all';
function updateSkills(){const query=skillSearch.value.trim().toLowerCase();let count=0;document.querySelectorAll('.skill-group').forEach(group=>{let visible=0;group.querySelectorAll('tbody tr').forEach(row=>{row.hidden=!(row.textContent.toLowerCase().includes(query)&&(filter==='all'||row.dataset.category===filter||row.dataset.mode===filter));if(!row.hidden){visible++;count++;}});group.hidden=visible===0;});document.querySelector('#skill-count').textContent=`顯示 ${count} / ${skillTotal} 個 skills`;document.querySelector('#skill-empty').hidden=count>0;}
skillSearch?.addEventListener('input',updateSkills);
document.querySelectorAll('[data-filter]').forEach(button=>button.addEventListener('click',()=>{filter=button.dataset.filter;document.querySelectorAll('[data-filter]').forEach(item=>{item.classList.toggle('active',item===button);item.setAttribute('aria-pressed',String(item===button));});updateSkills();}));
document.addEventListener('keydown',event=>{if(event.key==='/'&&!['INPUT','TEXTAREA'].includes(document.activeElement.tagName)){const field=topicSearch||skillSearch;if(field){event.preventDefault();field.focus();}}});
