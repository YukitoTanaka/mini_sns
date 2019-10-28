from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib.auth.models import User
from django.contrib import messages

from .models import Message,Friend,Group,Good
from .forms import GroupCheckForm,GroupSelectForm,SearchForm,FriendsForm,CreateGrouupForm,PostForm

from django.db.models import Q
from django.contrib.auth.decorators import login_required

import sys,traceback
# ログインしないとアクセスできなくなる@アノテーション

# indexのビュー関数 (searchform,checkform,messages(request.userは共通)の３つの変数を用意して返せば画面表示ができる)
@login_required(login_url='/admin/login/')
def index(request):
    #publicのuserを取得
    (public_user,public_group) = get_public()

    # POST送信時の処理
    if request.method == "POST":

        # Groupsのチェック更新時の処理
        if request.POST['mode'] == '__check_form__':
            # フォームの用意
            searchform = SearchForm()
            checkform = GroupCheckForm(request.user,request.POST)
            # チェックしたGroup名をリストに格納
            glist = []
            for item in request.POST.getlist("groups"):
                glist.append(item)
            # messageの取得
            messages = get_your_group_message(request.user,glist,None)

        # Groupsメニュー変更時の処理
        if request.POST['mode'] == '__search_form__':
            # フォームの用意
            searchform = SearchForm(request.POST)
            checkform = GroupCheckForm(request.user)
            # Groupのリストを取得
            gps = Group.objects.filter(owner = request.user)
            glist = [public_group]
            for item in gps:
                glist.append(item)
            # messageの取得
            messages = get_your_group_message(request.user, glist, request.POST["search"])

    # GETアクセス時の処理
    else:
        # フォームの用意
        searchform = SearchForm()
        checkform = GroupCheckForm(request.user)
        # Groupのリストを取得
        gps = Group.objects.filter(owner=request.user)
        glist = [public_group]
        for item in gps:
            glist.append(item)
        # messageの取得 (検索そのものはget_your_group_message関数を使う）
        messages = get_your_group_message(request.user, glist, None)

    #共通処理 (辞書に格納)
    params = {
        "login_user":request.user,
        "contents":messages,
        "check_form":checkform,
        "search_form":searchform,
    }
    return render(request,'mini_sns/index.html',params)


# groupsビュー関数 (グループとフレンドの管理ページの処理)
@login_required(login_url='/admin/login/')
def groups(request):
    # 登録したFriendの取得
    friends = Friend.objects.filter(owner = request.user)

    # POST送信時の処理 (送受信）
    if request.method == "POST":

        # Groupsメニュー選択肢の処理
        if request.POST["mode"] == "__groups_form__":
            # 選択したGroup名を取得
            sel_group = request.POST["groups"]
            # DBからGroupを取得
            gp = Group.objects.filter(owner =request.user).filter(title=sel_group).first()
            # Group内のFriendを取得
            fds = Friend.objects.filter(owner = request.user).filter(group=gp)
            # FriendのUserをリストに格納
            vlist = []
            for item in fds:
                vlist.append(item.user.username)
            # フォームの用意
            sys.stderr.write("5")
            groupsform = GroupSelectForm(request.user,request.POST)
            friendsform = FriendsForm(request.user,friends=friends,vals=vlist)

        # Friendsのチェック更新時の処理
        if request.POST["mode"] == "__friends_form__":
            # 選択したGroup名を取得
            sel_group = request.POST["groups"]
            group_obj = Group.objects.filter(title=sel_group).first()
            # チェックしたFriendsを取得
            sel_fds = request.POST.getlist("friends")
            # FriendsのUserを取得
            sel_users = User.objects.filter(username__in=sel_fds)
            # Userリストに含まれるユーザーが登録したFriendsを取得
            fds = Friend.objects.filter(owner=request.user).filter(user__in=sel_users)
            # FriendのUserをリストに格納
            vlist = []
            for item in fds:
                item.group = group_obj
                item.save()
                vlist.append(item.user.username)
            #メッセージを設定
            messages.success(request," フレンドを" + sel_group + "に登録しました。")
            # フォームの用意
            groupsform = GroupSelectForm(request.user, {"groups":sel_group})
            friendsform = FriendsForm(request.user, friends=friends, vals=vlist)

    # GETアクセス時の処理 (閲覧のみ）
    else:
        # フォームの用意
        groupsform = GroupSelectForm(request.user)
        friendsform = FriendsForm(request.user, friends=friends, vals=[])
        sel_group = '-'

    # 共通の処理
    createform = CreateGrouupForm()

    params = {
        "login_user":request.user,
        "gorups_form":groupsform,
        "friends_form":friendsform,
        "create_form":createform,
        "group":sel_group,
    }
    return render(request, 'mini_sns/groups.html',params)


# Friendビュー関数 (フレンド追加処理）
@login_required(login_url='/admin/login/')
def add(request):
    # 追加するUserを取得
    add_name = request.GET["name"]
    add_user = User.objects.filter(username=add_name).first()
    # Userが本人の場合の例外
    if add_user == request.user:
        messages.info(request, "フレンドに追加できません。")
        return redirect(to='/mini_sns')
    # publicの取得
    (public_user,public_group) = get_public()
    # add_userのFriendの数を取得 / 0より大なら既に登録済み
    frd_num = Friend.objects.filter(owner=request.user).filter(user=add_user).count()
    if frd_num > 0:
        messages.info(request,add_user.username + " は既に追加されています。")
        return redirect(to='/mini_sns')

    # Friendの登録処理
    frd = Friend()
    frd.owner = request.user
    frd.user = add_user
    frd.group = public_group
    frd.save()
    # メッセージを設定
    messages.success(request,add_user.username + " を追加しました。\
        groupページに移動して、追加したフレンドをメンバーに設定してください。")
    return redirect(to='/mini_sns')

# グループ作成処理
@login_required(login_url='/admin/login/')
def creategroup(request):
    # Groupを作り、Userとtitleを設定・保存する
    gp = Group()
    gp.owner  = request.user
    gp.title = request.POST["group_name"]
    gp.save()
    messages.info(request, "新しいグループ「 " + gp.title + " 」を作成しました。")
    return redirect(to='/mini_sns/groups')

# メッセージの投稿処理
@login_required(login_url='/admin/login/')
def post(request):

    # POST送信の処理
    if request.method == "POST":
        # 送信内容の取得
        gr_name = request.POST["groups"]
        content = request.POST["content"]
        # Groupの取得
        group = Group.objects.filter(owner=request.user).filter(title=gr_name).first()
        if group == None:
            (pub_user,group) = get_public()
        # Messageを作成・設定して保存
        msg = Message()
        msg.owner = request.user
        msg.group = group
        msg.content = content
        msg.save()
        # メッセージを設定
        messages.success(request, "新しいメッセージを投稿しました。")
        return redirect(to='/mini_sns')

    # GETアクセス時の処理
    else:
        form = PostForm(request.user)

    # 共通処理
    params = {
        "login_user":request.user,
        "form":form,
    }
    return render(request, 'mini_sns/post.html', params)


# 投稿シェアの処理
@login_required(login_url='/admin/login/')
def share(request, share_id):
    #シェアするMessageの取得
    share = Message.objects.get(id=share_id)

    # POST送信の処理(GETはない)
    if request.method == "POST":
        #送信内容を取得
        gr_name = request.POST["groups"]
        content = request.POST["content"]
        # Groupの取得
        group = Group.objects.filter(owner=request.user).filter(title=gr_name).first()
        if group == None:
            (pub_user,group) = get_public()
        # Messageを作成・設定して保存
        msg = Message()
        msg.owner = request.user
        msg.group = group
        msg.content = content
        msg.share_id = share_id
        msg.save()
        share_msg = msg.get_share()
        share_msg.share_count += 1
        share_msg.save()
        # メッセージを設定
        messages.success(request, "メッセージをシェアしました！")
        return redirect(to='/mini_sns')

    # 共通処理
    form = PostForm(request.user)
    params = {
        "login_user":request.user,
        "form":form,
        "share":share,
    }
    return render(request,'mini_sns/share.html', params)

# いいね goodボタンの処理
@login_required(login_url='/admin/login/')
def good(request,good_id):
    # いいねするMessageを取得
    good_msg = Message.objects.get(id=good_id)
    # 自分がいいねした数を調べる
    is_good = Good.objects.filter(owner=request.user).filter(message=good_msg).count()
    # 0 > なら既にいいね済み
    if is_good > 0:
        messages.success(request, "既に「いいね」済みです。")
        return redirect(to='/mini_sns')

    # いいね +1
    good_msg.good_count += 1
    good_msg.save()
    # goodを作成設定して保存
    good = Good()
    good.owner = request.user
    good.message = good_msg
    good.save()
    # メッセージを設定
    messages.success(request, "「いいね！」")
    return redirect(to='/mini_sns')


##（ビュー関数ではなく、内部で使う関数）
## 指定グループ、文字検索によるMessageの取得
def get_your_group_message(owner, glist, find):
    # publicの取得
    (public_user,public_group) = get_public()
    # チェックされたGroupの取得
    groups = Group.objects.filter(Q(owner=owner)|Q(owner=public_user)).filter(title__in=glist)
    # Groupに含まれるFriendsの取得
    my_friends = Friend.objects.filter(group__in=groups)
    # Friends のUserをリストに格納
    my_users = []
    for f in my_friends:
        my_users.append(f.user)
    # UserリストのUserが作ったGroupの取得
    his_groups = Group.objects.filter(owner__in=my_users)
    his_friends = Friend.objects.filter(user=owner).filter(group__in=his_groups)
    my_groups = []
    for hf in his_friends:
        my_groups.append(hf.group)

    # 文字検索なし -> groupがhis_groupsに含まれるMessageを取得
    # 文字検索あり -> 更に検索ワードに合致するMessageを取得
    if find == None:
        messages = Message.objects.filter(Q(group__in=groups)|Q(group__in=my_groups))[:100]
    else:
        messages = Message.objects.filter(Q(group__in=groups)|Q(group__in=my_groups))\
                       .filter(content__contains=find)[:100]
    return messages

## publicなUserとGroupの取得関数
def get_public():
    public_user = User.objects.filter(username="public").first()
    public_group = Group.objects.filter(owner=public_user).first()
    return (public_user,public_group)

