# vmchub
---
OSC Port Forwarder / OSC animation capture and replay for Vtubing
---
This app allows you to forward multiple sources of VMC/OSC traffic (like VeeSeeFace) to one consumer (like VtuberPlus). 

It also provides capture and replay to facilitate idle animations

--
Dependencies - (let me know if I missed one!)
--

pip install pyqt6            
pip install python-osc       
pip install SocketServer 
pip install pyinstaller 

--
Building windows exe
--
pyinstaller --onefile --windowed --add-data "star.png;." .\vmchub.py

---
Running
---
python .\vmchub.py
