# vmchub
---
OSC Port Forwarder / OSC animation capture and replay for Vtubing
---
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
