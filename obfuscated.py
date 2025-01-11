_L='Preferences'
_K='<Escape>'
_J='-topmost'
_I='height'
_H='width'
_G='error'
_F='Inter'
_E=False
_D='y'
_C='w'
_B=True
_A=None
import tkinter as tk
from tkinter import simpledialog
from PIL import ImageGrab,Image,ImageTk
import pytesseract,pystray
from pystray import MenuItem as item
from pynput import keyboard
import requests,os,json
from pytesseract import Output
import customtkinter as ctk
from typing import Dict,Any,Tuple,List,Union
import textwrap,re,asyncio,threading,math
from nltk.corpus import words
from nltk.corpus import wordnet as wn
import nltk
from nltk import download
download('wordnet')
nltk.download('words')
BASE_DIR=os.path.dirname(__file__)
TESSERACT_PATH=os.path.join(BASE_DIR,'bin','tesseract.exe')
TESSDATA_PATH=os.path.join(BASE_DIR,'bin','tessdata')
SHORTCUT='<ctrl>+<alt>+s'
API_URL='https://api.dictionaryapi.dev/api/v2/entries/en/'
CACHE_FILE='dictionary_cache.json'
pytesseract.pytesseract.tesseract_cmd=TESSERACT_PATH
os.environ['TESSDATA_PREFIX']=TESSDATA_PATH
cache={}
screenshot_window=_A
current_overlay=_A
is_active=_E
is_root_destroyed=_E
def load_cache():
	global cache
	try:
		with open(CACHE_FILE,'r')as A:cache=json.load(A)
	except FileNotFoundError:cache={}
def save_cache():
	with open(CACHE_FILE,_C)as A:json.dump(cache,A)
load_cache()
def fetch_definition(word):
	A=word;A=A.lower()
	if A in cache:return cache[A]
	B=requests.get(f"{API_URL}{A}")
	if B.status_code==200:C=B.json();cache[A]=C;save_cache();return C
	else:return{_G:f"Word '{A}' not found."}
class ScreenshotWindow:
	def __init__(A):B='black';global is_active,is_root_destroyed;is_root_destroyed=_E;is_active=_B;A.root=tk.Tk();A.root.attributes('-fullscreen',_B);A.root.attributes(_J,_B);A.screen=ImageGrab.grab();A.screen_photo=ImageTk.PhotoImage(A.screen);A.canvas=tk.Canvas(A.root,bg=B);A.canvas.pack(fill=tk.BOTH,expand=_B);A.canvas.create_image(0,0,anchor=tk.NW,image=A.screen_photo);A.loading_label=tk.Label(A.root,text='Processing OCR...',font=('Helvetica',20),fg='white',bg=B);A.loading_label.place(relx=.5,rely=.05,anchor='center');A.root.config(cursor='wait');A.canvas.bind('<Button-1>',A.on_click);A.root.bind(_K,A.on_escape);A.ocr_done=asyncio.Event();A.processing_ocr=_E
	async def process_ocr(A):
		C='text';A.processing_ocr=_B;F=ImageGrab.grab();A.ocr_data=pytesseract.image_to_data(F,output_type=Output.DICT);A.characters=[]
		for B in range(len(A.ocr_data[C])):
			if A.ocr_data[C][B].strip():
				D=A.ocr_data[C][B];G=A.ocr_data['left'][B];H=A.ocr_data['top'][B];I=A.ocr_data[_H][B];J=A.ocr_data[_I][B];K=A.ocr_data['conf'][B]
				for(L,M)in enumerate(D):E=I/len(D);N=G+L*E;A.characters.append((M,int(N),H,int(E),J,K))
		A.processing_ocr=_E;A.ocr_done.set();A.loading_label.destroy();A.root.config(cursor='');await asyncio.sleep(1)
	def on_click(A,event):
		B=event
		if A.processing_ocr:A.ocr_done.clear();asyncio.ensure_future(A.wait_for_ocr(B.x,B.y))
		else:A.handle_click(B.x,B.y)
	async def wait_for_ocr(A,x,y):await A.ocr_done.wait();A.handle_click(x,y)
	def find_closest_chars(J,x,y,radius=70):
		'Find closest character and nearby characters within radius.';I='distance';A=[]
		for(K,B,C,D,E,L)in J.characters:
			F=B+D/2;G=C+E/2;H=math.sqrt((x-F)**2+(y-G)**2)
			if H<=radius:A.append({'char':K,I:H,'x':B,_D:C,_H:D,_I:E,'center_x':F,'center_y':G})
		if not A:return{},[]
		A.sort(key=lambda x:x[I]);return A[0],A
	def find_possible_words(U,x,y,radius=70):
		'Find all possible words containing the character at clicked position.';F,L=U.find_closest_chars(x,y,radius)
		if not F or not L:return[]
		G={};V=F[_D];W=max(A[_I]for A in L)*.5
		for N in L:
			D=N[_D]
			if abs(D-V)<=W:
				if D not in G:G[D]=[]
				G[D].append(N)
		for D in G:G[D].sort(key=lambda x:x['x'])
		J=_A
		for(D,O)in G.items():
			if any(A['x']==F['x']and A[_D]==F[_D]for A in O):J=O;break
		if not J:return[]
		C=[(A['char'],A['x'],A[_D],A[_H],A[_I])for A in J];K=next(A for(A,(D,B,C,E,G))in enumerate(C)if B==F['x']and C==F[_D]);P=[];X=sum(A[_H]for A in J)/len(J);Q=X*1.5
		for E in range(K,-1,-1):
			if E<K and C[E+1][1]-(C[E][1]+C[E][3])>Q:break
			for H in range(K,len(C)):
				if H>0 and C[H][1]-(C[H-1][1]+C[H-1][3])>Q:break
				A=''.join(A for(A,*B)in C[E:H+1]);A=re.sub('^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$','',A)
				if A and len(A)>1:Y=(H-E)/2;Z=abs(K-E-Y);P.append((A,Z,len(A)))
		B=[];M=set()
		for(A,R,S)in P:
			if A.lower()not in M:
				A=A.lower()
				if A in cache:B.append((A,R,S));M.add(A)
				else:
					a=nltk.corpus.wordnet.synsets(A)
					if a:B.append((A,R,S));M.add(A)
		B.sort(key=lambda x:(-x[2],x[1],x[0]))
		if len(B)>1 and B[1][0]:
			if B[0][0]==B[1][0]+'s':I=B[1][0]
			elif B[0][0]==B[1][0]+'ed':I=B[1][0]
			else:I=B[0][0]if B else _A
		else:I=B[0][0]if B else _A
		if I:cache[I]=fetch_definition(I);save_cache()
		T=[A for(A,B,B)in B];print('Found valid words:',T);return T
	def handle_click(D,x,y):
		'Process click and show word definition.';global current_overlay
		try:
			if current_overlay and current_overlay.root.winfo_exists():current_overlay.root.destroy();current_overlay=_A
		except tk.TclError:current_overlay=_A
		C=D.find_possible_words(x,y)
		if C:
			A=C[0];B=cache.get(A.lower(),_A)
			if B is _A:B=fetch_definition(A)
			current_overlay=ModernDictionaryOverlay(x,y,A,B);current_overlay.show();return
		current_overlay=ModernDictionaryOverlay(x,y,'No valid word detected.',{_G:'No valid word detected at this position'});current_overlay.show()
	def on_escape(A,event):
		global current_overlay,screenshot_window,is_active,is_root_destroyed
		if not is_active or is_root_destroyed:return
		if current_overlay and current_overlay.root:
			try:
				if current_overlay.root.winfo_exists():current_overlay.root.destroy();current_overlay=_A
			except tk.TclError:current_overlay=_A
		is_root_destroyed=_B;is_active=_E
		try:A.root.quit();A.root.destroy()
		except tk.TclError:pass
		screenshot_window=_A;restart_listener()
class ModernDictionaryOverlay(ctk.CTkFrame):
	def __init__(A,x,y,word,data):C='-alpha';B='#1E1E1E';A.root=ctk.CTk();A.root.attributes(C,.0);A.root.overrideredirect(_B);A.root.attributes(_J,_B);super().__init__(master=A.root,fg_color=B,border_color='1E1E1E',border_width=0,corner_radius=15);A.pack(fill='both',expand=_B,padx=2,pady=2);A.grid_columnconfigure(0,weight=1);A.title=ctk.CTkLabel(A,text=word.capitalize(),font=ctk.CTkFont(family=_F,size=14,weight='bold'),text_color='#FFFFFF');A.title.grid(row=0,column=0,padx=15,pady=(10,5),sticky=_C);A.content_frame=ctk.CTkScrollableFrame(A,fg_color=B,corner_radius=15,border_color=B,border_width=0,height=300);A.content_frame.grid(row=1,column=0,sticky='nsew',padx=10);A.content_frame.grid_columnconfigure(0,weight=1);A._add_content(data);A.root.geometry('500x1');A.root.update();A._adjust_window_size();A.root.update();A._position_window(x,y);A.root.bind(_K,lambda e:A.root.destroy());A.root.bind('<FocusOut>',lambda e:A.root.destroy());A.root.focus_force();A.root.grab_set();A.root.attributes(C,.95)
	def _position_window(C,x,y):
		H=C.get_screen_width();I=C.get_screen_height();D=C.root.winfo_width();E=C.root.winfo_height();F=x<H/2;G=y<I/2
		if F and G:A=x;B=y
		elif not F and G:A=x-D;B=y
		elif F and not G:A=x;B=y-E
		else:A=x-D;B=y-E
		A=max(0,min(A,H-D));B=max(0,min(B,I-E));C.root.geometry(f"+{A}+{B}")
	def _adjust_window_size(A):C=sum(A.winfo_reqheight()for A in A.content_frame.winfo_children())+30;D=C+90;B=min(D,400);A.content_frame.configure(height=B-60);A.root.geometry(f"500x{B}")
	def get_screen_width(A):return A.root.winfo_screenwidth()
	def get_screen_height(A):return A.root.winfo_screenheight()
	def _show_window(A):A.root.deiconify();A.root.lift();A.root.focus_force();A.root.attributes(_J,_B);A.root.update()
	def _on_escape(A,event):A.root.quit();A.root.destroy()
	def _on_focus_out(A,event):
		if not A.root.focus_get():A.root.quit();A.root.destroy()
	def _add_content(C,data):
		I='example';H='synonyms';G='meanings';B=data
		if isinstance(B,dict):
			if _G in B:J=ctk.CTkLabel(C.content_frame,text=B[_G],font=ctk.CTkFont(family=_F,size=12),text_color='#FF6B6B',wraplength=300);J.grid(row=0,column=0,padx=5,pady=5,sticky=_C);return
			F=B.get(G,[])
		else:F=B[0].get(G,[])if B else[]
		A=0
		for D in F:
			K=ctk.CTkLabel(C.content_frame,text=D['partOfSpeech'],font=ctk.CTkFont(family=_F,size=12,weight='bold'),text_color='#4D96FF');K.grid(row=A,column=0,padx=5,pady=(5,2),sticky=_C);A+=1
			if D.get(H):L='Synonyms: '+', '.join(D[H][:5]);M=ctk.CTkLabel(C.content_frame,text=L,font=ctk.CTkFont(family=_F,size=10),text_color='#6C757D',wraplength=300);M.grid(row=A,column=0,padx=(15,5),pady=(2,5),sticky=_C);A+=1
			for E in D.get('definitions',[]):
				N=textwrap.fill(E['definition'],width=75);O=ctk.CTkLabel(C.content_frame,text=f"• {N}",font=ctk.CTkFont(family=_F,size=11),text_color='#CCCCCC',wraplength=450,justify='left');O.grid(row=A,column=0,padx=(15,5),pady=2,sticky=_C);A+=1
				if I in E:P=textwrap.fill(f'"{E[I]}"',width=70);Q=ctk.CTkLabel(C.content_frame,text=P,font=ctk.CTkFont(family=_F,size=10,slant='italic'),text_color='#888888',wraplength=320);Q.grid(row=A,column=0,padx=(25,5),pady=(0,2),sticky=_C);A+=1
	def show(A):A.root.mainloop()
def get_closest_character(click_x,click_y,character_positions):
	'\n    Find the character closest to the click position.\n    ';A=float('inf');B=_A;C=-1
	for(E,(F,G,H,I,J))in enumerate(character_positions):
		K,L=G+I/2,H+J/2;D=math.sqrt((click_x-K)**2+(click_y-L)**2)
		if D<A:A=D;B=F;C=E
	return B,C
def generate_word_candidates(character_positions,start_index):
	'\n    Generate all possible word candidates centered on the start index.\n    ';B=start_index;A=character_positions;C=[];G=A[B][0]
	for D in range(B,-1,-1):
		if not A[D][0].isalnum():break
		for E in range(B,len(A)):
			if not A[E][0].isalnum():break
			F=''.join([B for(B,A,A,A,A)in A[D:E+1]])
			if G in F:C.append(F)
	return C
def validate_words(candidates):
	B=[]
	for A in candidates:
		A=A.lower()
		if A in cache:B.append(A)
		else:
			C=requests.get(f"{API_URL}{A}")
			if C.status_code==200:cache[A]=C.json();B.append(A);save_cache()
	return B
def capture_screen():
	global screenshot_window
	if screenshot_window is _A:screenshot_window=ScreenshotWindow();threading.Thread(target=asyncio.run,args=(screenshot_window.process_ocr(),)).start();screenshot_window.root.mainloop()
def show_definition(word,x,y,data):A=ModernDictionaryOverlay(x,y,word,data);A.show()
def setup_tray_icon():
	def B():A.stop()
	C=item(_L,preferences),item('Exit',B);D=Image.open('icon.png');A=pystray.Icon('WordPicker',icon=D,menu=C);A.run()
def preferences():
	global SHORTCUT,listener;A=tk.Tk();A.withdraw()
	if listener is not _A:listener.stop()
	B=simpledialog.askstring(_L,'Enter a new shortcut (e.g., ctrl+alt+x):')
	if B:SHORTCUT=B;setup_shortcut()
	A.destroy()
def on_activate():capture_screen()
listener=_A
def restart_listener():
	global listener
	if listener and listener.is_alive():listener.stop()
	setup_shortcut()
def setup_shortcut():global listener;listener=keyboard.GlobalHotKeys({SHORTCUT:on_activate});listener.start()
def main():setup_shortcut();setup_tray_icon()
if __name__=='__main__':main()