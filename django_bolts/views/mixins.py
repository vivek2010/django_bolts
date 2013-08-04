
from django_bolts.views.decorators import view, hijax_view
from django.shortcuts import get_object_or_404,render
from django.contrib.auth.models import User
   
class CRUDResourceMixin(object):

    @view('(\d+)')
    def delete(self,request,mid):
        obj = get_object_or_404(self.model,pk=mid)
        user = request.user
    
    @view(r'(\d+)',name='')
    def detail(self,request,mid):        
        obj = get_object_or_404(self.model,pk=int(mid))                                        
        ctx = {'object':obj}        
        template = self.get_template_name('detail')        
        response = render(request,template,ctx)
        return response    
    
    @view()
    def list(self,request):        
        ctx = {'title':self.plural_label}
        object_list = self.model.objects.all()
        return self.render_list(request,object_list,ctx)        
    
    @view()
    def query(self,request):
        ctx = {'title':'Search Results'}
        query = request.GET.get('query',None)
        if not query: return self.list(request)    
        object_list = self.model.objects.search(query)     
        ctx['query'] = query    
        return self.render_list(request, object_list, ctx)
          
    def render_list(self,request,object_list,ctx):            
        template = self.get_template_name('list')
        ctx['object_list'] = object_list
        return render(request, template, ctx)                             


class SocialResourceMixin(object):
            
    @view(r'(\d+)')
    def favorite_top(self,request,mid):
        return self.render_favorites(request,mid,8)
    
    @view(r'(\d+)')
    def favorite_all(self,request,mid):
        return self.render_favorites(request,mid)   
    
    def render_favorites(self,request,mid,total=0,search=None):
        user = get_object_or_404(User,pk=mid)
        ctx = {}        
        object_list = self.model.objects.select_related('favorites').filter(favorites__owner=user).all()                     
        rnd = cutils.Listing(object_list)
        return rnd.render(request,ctx,self.get_template_name("%s_favorites"),total=total)              
    
    @hijax_view(r'(\d+)')
    def like(self,user,mid):        
        obj = get_object_or_404(self.model,pk=mid)        
        obj.add_like(user)
        return {'total':obj.total_likes,'message':'Successfully liked !','next_url':obj.get_absolute_url()}        
           
    @hijax_view(r'(\d+)')
    def favorite_add(self,user,mid):        
        obj = get_object_or_404(self.model,pk=mid)
        obj.add_favorite(user)
        msg = "Successfully added to favorites"
        return {'total':obj.total_favorites,'message':msg,'next_url':obj.get_absolute_url()}  
    
    @hijax_view(r'(\d+)')
    def favorite_remove(self,user,mid):        
        obj = get_object_or_404(self.model,pk=mid)
        obj.remove_favorite(user)
        msg = 'Successfully removed from favorites'
        return {'total':obj.total_favorites,',message':msg,'next_url':obj.get_absolute_url() }
            
    @hijax_view(r'(\d+)',csrf=False)
    def comment_remove(self,user,mid):        
        obj = get_object_or_404(self.model,pk=mid)
        obj.remove_comment(user)
        msg = ''        
        return {'total':obj.total_comments,'message':msg,'next_url':obj.get_absolute_url()}                

    def create_comment(self,request,obj,commit=True):        
        created = False   
        if request.method == 'POST':
            form = cforms.CommentForm(request.POST)
            if form.is_valid():
                ins = form.save(request,obj)
                obj.total_comments += 1
                if commit: obj.save()
                created = True                 
        else:
            form = cforms.CommentForm()
        return form,created
    
    @view(r'(\d+)')
    def comment_add(self,request,mid):
        item = get_object_or_404(self.model,pk=mid)        
        ctx = {}
        form,created = self.create_comment(request, item)
        if created: 
            return post_result(request,)
        ctx['form']  = form    
        return render(request,"commons/form.html",ctx)        
        
    @view(r'(\d+)')
    def comment_top(self,request,mid):
        return self.render_comments(request, mid,10)
    
    @view(r'(\d+)')    
    def comment_all(self,request,mid):
        return self.render_comments(request, mid)
    
    def render_comments(self,request,mid,total=0,search=None):
        item = get_object_or_404(self.model,pk=mid)
        object_list = Comment.objects.filter(object_id=item.id).all()
        ls = cutils.Listing(object_list)        
        comment_form = cforms.CommentForm()        
        ctx = {'comment_form':comment_form}
        template = self.get_template_name("%s_comments")
        return ls.render(request,template,ctx,total=total)    

    