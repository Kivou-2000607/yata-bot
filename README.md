# YATA discord bot - a discord bot made for Torn
If you want the bot on your server DM me

## Features
* **Verify accounts:** verifies discord accounts (*i.e.* makes a link between discord and Torn account) based on official Torn server verification or API key.
* **Faction role:** can attribute roles based on factions and check easily the membership over time.
* **Loot functions:** gives NPC reports to loot level IV:
```
NPC report of 19/12/05 21:01:03 TCT for Kivou [2000607]
Duke   : [====================] (100%) 00hrs 02mins 03s since loot level IV [20:59:00 TCT]
Scrooge: [=================   ] ( 88%) 00hrs 24mins 26s to loot level IV [21:25:29 TCT]
Leslie : [                    ] (  0%) 04hrs 27mins 49s to loot level IV [01:28:52 TCT]
```
and notifies **@Looter** 5 minutes before reaching loot level IV.
* **Stock sharing:** Only for `wssb` and `tcb`, gives stock status of sharing group **@wssb** or **@tcb**:
```
NAME            | EDU TIME LEFT | WSSB
 --------------------------------------
userA           |  0d  5h 31min |  x  
userB           |  5d 15h 56min |     
userC           |  8d  8h 15min |     
userD           |  8d 11h 55min |  x  
```
* and minor other functions

## Server owners
To have the bot on you server read the following and DM me.

### **Step 1**: tell me your options
* Verify accounts [Yes/No]
    * Force verification [Yes/No] *will send a DM to new members explaining how to get verified*
    * The users you want for the key usage (they have to be on YATA)
    * The factions you want as roles (your faction and your allies for example, they have to be on YATA too)
* Loot bot [Yes/No]
* Stocks [Yes/No]

### **Step 2**: what you need to do on your server
**Before inviting the bot read the following**. The bot will do a couple of things when he'll join (creating channels and roles) depending on your options.

As a general set of rules:
1. you can move channels (created by the bot) around but don't change their name and don't have the same name for different channels.
2. The **@YATA** role has to be above the roles he's managing. Don't change their name.

* Verify
    * creates **@Verified** role and a **@Faction [id]** role / faction
    * creates **#yata-admin** channel (only seen by server owner)
    * creates **#verify-id** channel that becomes the system channel
* Loot
    * creates **@Looter** role
    * creates **#start-looting** and **#loot** channel
* Stocks
    * creates **@wssb** and **@tcb** roles
    * creates **#wssb** and **#tcb** channels

If you read all of this you can invite the bot. I'll have to reboot it to account for you options so keep me in the loop.

Enjoy,

Kivou [2000607]
