
# A GUI for data transfer and visualization

Currently in test. Only tested with STM32F3 MCUs.

<img src='./misc/demo.gif'>


## Requirements

- tkinter
- matplotlib
- pyserial

## Running

```bash
  git clone --recurse-submodules https://github.com/blr-ophon/visuvia
```

```bash
  python main.py --gui 
```
or 

```bash
  python main.py --cmd
```

## Usage

Use the MCTP api (still to be documented) on your MCU to communicate with visuvia.
GUI allows data visualization in real time, cmd saves  received data to csv and text files.


## CMD commands

**sync**: Try to connect to microcontroller.
**drop**: Disconnect from microcontroller.
**request**: Start receiving data.
**stop**: Stop data transfer. Save data to csv and text files.
**exit**: Exit visuvia cmd.
