while [ 1 ] 
do 
  if [ 1=`ps -ax | grep "python utilsgmail.py" | wc -l` ] 
  then   
    python utilsgmail.py  
  fi 
  sleep 2
done
