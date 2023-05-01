# python main.py --datasets 9 \
#                --algorithms lscen lsci lsbda gssci gsci \
#                --comm_type all \
#                --comm_range 5 \
#                --comm_rate 2.5 \
#                --dt 0.1 \
#                --offset 360 \
#                --duration 20

sudo python main.py --path /data/herh/utias/ \
               --datasets 9 \
               --algorithms lscen lsci lssci lsbda gsci \
               --comm_type all \
               --comm_range 5 \
               --comm_rate 2.5 \
               --dt 0.05 \
               --offset 1500 \
               --duration 25
